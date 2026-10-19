"""Editable grid world and 50- or 100-cell four-action spiking controllers.

Only eight declared binary observations enter the controller. Environment
transitions and feedback follow action selection; no route solver chooses it.
"""

from dataclasses import dataclass, asdict
import copy
import hashlib
import json
import math

import numpy as np

from .continuing import ContinuingNetwork, RewardParameters
from .network import Network, Synapse
from .laboratory import ActivityWindow

ACTIONS = ('Up', 'Right', 'Down', 'Left')
DELTAS = ((-1, 0), (0, 1), (1, 0), (0, -1))
SENSOR_NAMES = ('Goal up', 'Goal right', 'Goal down', 'Goal left',
                'Unsafe up', 'Unsafe right', 'Unsafe down', 'Unsafe left')
SENSORS = tuple(tuple(range(i*3, i*3+3)) for i in range(8))
MOTORS = tuple(tuple(range(24+i*5, 29+i*5)) for i in range(4))
INHIBITORY = tuple(range(44, 50))
MODES = ('learning', 'learning_disabled', 'random_feedback')
MAX_MOVES = 5000


@dataclass(frozen=True)
class CircuitProfile:
    n_neurons: int
    sensors: tuple
    motors: tuple
    inhibitory: tuple
    weight_scale: float

    @property
    def adaptive_count(self):
        return sum(map(len,self.sensors))*sum(map(len,self.motors))


def circuit_profile(n_neurons=50):
    if type(n_neurons) is not int or n_neurons not in (50,100):
        raise ValueError('Choose the 50-cell earlier arena or the 100-cell movement microscope.')
    if n_neurons==50: return CircuitProfile(50,SENSORS,MOTORS,INHIBITORY,1.)
    return CircuitProfile(100,
        tuple(tuple(range(i*6,i*6+6)) for i in range(8)),
        tuple(tuple(range(48+i*10,58+i*10)) for i in range(4)),
        tuple(range(88,100)),.5)


def held_out_pair(start, goal):
    """Fixed pair partition, independent of policy, outcomes and training seed."""
    distance = abs(start[0]-goal[0])+abs(start[1]-goal[1])
    return distance >= 2 and ((start[0]*5+start[1])*31+(goal[0]*5+goal[1])*17) % 7 == 0


def cell(value):
    if not isinstance(value, (tuple, list)) or len(value) != 2 or any(type(x) is not int or not 0 <= x < 5 for x in value):
        raise ValueError('cells must be [row, column] integers in 0..4')
    return tuple(value)


@dataclass(frozen=True)
class World:
    walls: tuple = ()
    hazards: tuple = ()
    max_steps: int = 20
    feedback: str = 'shaped'

    def __post_init__(self):
        for name in ('walls', 'hazards'):
            values = getattr(self, name)
            if not isinstance(values, tuple) or any(cell(v) != v for v in values) or len(set(values)) != len(values):
                raise ValueError('walls and hazards must be unique tuples of cells')
        if len(self.walls) > 12 or len(self.hazards) > 8 or set(self.walls) & set(self.hazards):
            raise ValueError('use at most 12 walls and 8 non-overlapping hazards')
        if type(self.max_steps) is not int or not 4 <= self.max_steps <= 32 or self.feedback not in ('shaped', 'sparse'):
            raise ValueError('step limit must be 4..32 and feedback shaped or sparse')
        safe = self.safe_cells
        if len(safe) < 2:
            raise ValueError('at least two safe cells are needed')
        # Connectivity is a map validity check, never an action-selection input.
        reached = {safe[0]}; todo = [safe[0]]
        for r, c in todo:
            for dr, dc in DELTAS:
                q = (r+dr, c+dc)
                if q in safe and q not in reached:
                    reached.add(q); todo.append(q)
        if len(reached) != len(safe):
            raise ValueError('safe cells must be connected; change walls or hazards')

    @property
    def safe_cells(self):
        return tuple((r, c) for r in range(5) for c in range(5)
                     if (r, c) not in self.walls and (r, c) not in self.hazards)

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict): raise ValueError('invalid world')
        try:
            return cls(tuple(cell(x) for x in value['walls']), tuple(cell(x) for x in value['hazards']),
                       value['max_steps'], value['feedback'])
        except (KeyError, TypeError) as exc: raise ValueError('invalid world') from exc


def observe(world, position, goal):
    r, c = cell(position); gr, gc = cell(goal)
    return np.array([gr < r, gc > c, gr > r, gc < c] +
                    [not (0 <= r+dr < 5 and 0 <= c+dc < 5) or (r+dr, c+dc) in world.walls or (r+dr, c+dc) in world.hazards
                     for dr, dc in DELTAS], dtype=float)


def transition(world, position, goal, action, step):
    position, goal = cell(position), cell(goal)
    if type(action) is not int or action not in range(4) or type(step) is not int or not 1 <= step <= world.max_steps:
        raise ValueError('invalid action or episode step')
    dr, dc = DELTAS[action]; q = (position[0]+dr, position[1]+dc)
    collision = not (0 <= q[0] < 5 and 0 <= q[1] < 5) or q in world.walls
    if collision: q = position
    success = q == goal
    hazard = q in world.hazards
    terminal = success or hazard or step == world.max_steps
    distance = lambda p: abs(p[0]-goal[0])+abs(p[1]-goal[1])
    if success: reward = 1.0
    elif hazard: reward = -1.0
    elif collision: reward = -.8
    elif world.feedback == 'shaped': reward = .4 * (distance(position)-distance(q)) - .02
    else: reward = -.02
    return {'after':list(q), 'collision':collision, 'hazard':hazard, 'success':success,
            'terminal':terminal, 'reward':reward,
            'distance_before':distance(position), 'distance_after':distance(q)}


def build_network(rng, n_neurons=50):
    profile=circuit_profile(n_neurons);scale=profile.weight_scale
    sources=sum(profile.sensors,());targets=sum(profile.motors,())
    edges = []
    for source in sources:
        for target in targets:
            edges.append(Synapse(source, target, float(np.clip(rng.normal(.022, .0005), .020, .024))*scale, 1.0))
    selected = tuple(range(len(edges)))
    for source in targets:
        for target in profile.inhibitory: edges.append(Synapse(source, target, .1*scale, 1.0))
    for source in profile.inhibitory:
        for target in targets: edges.append(Synapse(source, target, -.008*scale, 1.0))
    return Network(profile.n_neurons, tuple(edges), inhibitory_neurons=profile.inhibitory), selected


def probabilities(scores, exploration=.2):
    scores = np.asarray(scores, dtype=float)
    if scores.shape != (4,) or not np.isfinite(scores).all() or not math.isfinite(exploration) or not 0 <= exploration <= 1:
        raise ValueError('four finite action scores and exploration in [0,1] required')
    logits = np.clip((scores-scores.max())/.5, -60, 0)
    p = np.exp(logits); p /= p.sum()
    return exploration/4 + (1-exploration)*p


class ArenaSession:
    def __init__(self, seed=7, *, world=None, mode='learning', n_neurons=50):
        if type(seed) is not int or not 0 <= seed < 2**32 or mode not in MODES:
            raise ValueError('invalid arena seed or feedback condition')
        self.seed, self.mode = seed, mode
        self.profile=circuit_profile(n_neurons)
        self.world = world if world is not None else World()
        if not isinstance(self.world, World): raise ValueError('world must be World')
        children = np.random.SeedSequence(seed).spawn(4)
        network_rng, self.world_rng, self.policy_rng, self.feedback_rng = [np.random.default_rng(s) for s in children]
        network, selected = build_network(network_rng,self.profile.n_neurons)
        scale=self.profile.weight_scale
        self.engine = ContinuingNetwork(network, dt_ms=.5, eligible_synapses=selected,
            reward_parameters=RewardParameters(learning_rate_nA=.04*scale, w_min_nA=.002*scale, w_max_nA=.06*scale))
        self.initial_weights = self.engine.weights.copy()
        self.records, self.episodes = [], []
        self.position = self.goal = None
        self.episode_start = None
        self.episode_steps = 0
        self.done = True
        self.last_window = None

    def reset_dynamics(self):
        old = self.engine
        fresh = ContinuingNetwork(old.network, dt_ms=old.dt_ms, eligible_synapses=old.selected,
                                  reward_parameters=old.reward_parameters)
        fresh.weights[:] = old.weights
        fresh.tick = old.tick
        self.engine = fresh

    def begin_episode(self, start=None, goal=None, *, distance=None):
        if not self.done: raise ValueError('finish the current episode before starting another')
        safe = self.world.safe_cells
        if start is None and goal is None:
            distance = distance if distance is not None else (1 if len(self.episodes) < 40 else 2 if len(self.episodes) < 80 else 4)
            pairs = [(s, g) for s in safe for g in safe if 0 < abs(s[0]-g[0])+abs(s[1]-g[1]) <= distance and not held_out_pair(s,g)]
            if not pairs: raise ValueError('no safe start/goal pair at this curriculum distance')
            start, goal = pairs[int(self.world_rng.integers(len(pairs)))]
        else:
            start, goal = cell(start), cell(goal)
        if start not in safe or goal not in safe or start == goal:
            raise ValueError('start and goal must be distinct safe cells')
        self.reset_dynamics()
        self.last_window = None
        self.position, self.goal = tuple(start), tuple(goal)
        self.episode_start = self.position
        self.episode_steps = 0
        self.done = False

    def step(self, *, frozen=False, record=False):
        if type(frozen) is not bool or type(record) is not bool: raise ValueError('boolean step flags required')
        if len(self.records) >= MAX_MOVES: raise ValueError('arena reached its 5,000-move session budget')
        if self.done: self.begin_episode()
        before = self.position; observation = observe(self.world, before, self.goal)
        initial = self.engine.weights.copy(); blocks = []
        start = self.engine.time_ms
        def advance(duration, current=0):
            b = self.engine.advance(duration, current, record=record)
            if record: blocks.append(b)
        with self.engine.record_transmissions() as arrivals:
            drive = np.zeros(self.profile.n_neurons)
            for i, ids in enumerate(self.profile.sensors): drive[list(ids)] = .8*observation[i]
            advance(5, drive); advance(15)
            scores = np.array([self.engine.voltage[list(ids)].mean()-self.engine.network.neuron.rest_mV for ids in self.profile.motors])
            probs = probabilities(scores)
            # Frozen evaluation uses greedy neural scores, with seeded tie-breaking.
            if frozen:
                tied = np.flatnonzero(scores == scores.max())
                probs = np.zeros(4); probs[tied] = 1/len(tied)
            action = int(self.policy_rng.choice(4, p=probs))
            motor = np.zeros(self.profile.n_neurons); motor[list(self.profile.motors[action])] = .8
            advance(5, motor); advance(10)
            outcome = transition(self.world, before, self.goal, action, self.episode_steps+1)
            delivered = float(self.feedback_rng.choice([-1., 1.])) if self.mode == 'random_feedback' and not frozen else outcome['reward']
            # Map signed environmental feedback onto the existing centered rule.
            update = self.engine.feedback((delivered+1)/2, learning_enabled=not frozen and self.mode != 'learning_disabled')
            advance(65)
        self.position = tuple(outcome['after']); self.episode_steps += 1; self.done = outcome['terminal']
        row = {'move':len(self.records), 'episode':len(self.episodes), 'step':self.episode_steps,
               'before':list(before), 'goal':list(self.goal), 'observation':observation.tolist(),
               'action':action, 'scores_mV':scores.tolist(), 'probabilities':probs.tolist(),
               'frozen':frozen, 'delivered_feedback':delivered, 'update_l2_nA':float(np.linalg.norm(update)),
               'time_start_ms':start, **outcome}
        self.records.append(row)
        if self.done:
            rows = self.records[-self.episode_steps:]
            self.episodes.append({'episode':len(self.episodes), 'start':list(self.episode_start), 'goal':list(self.goal),
                                  'steps':self.episode_steps, 'success':outcome['success'], 'hazard':outcome['hazard'],
                                  'collisions':sum(r['collision'] for r in rows),
                                  'return':float(sum(r['reward'] for r in rows))})
        self.last_window = ActivityWindow.from_blocks(row['move'],blocks,initial,self.engine.weights,arrivals) if record else None
        return copy.deepcopy(row), self.last_window

    def train(self, episodes=20):
        if type(episodes) is not int or not 1 <= episodes <= 40: raise ValueError('train one to forty episodes per batch')
        target = len(self.episodes)+episodes
        while len(self.episodes) < target:
            self.step(record=len(self.episodes) == target-1)
        return self.episodes[-episodes:]

    def state_dict(self):
        return {'format':'synapse-arena-session-v1', 'seed':self.seed, 'mode':self.mode, 'world':asdict(self.world),
                **({'neurons':self.profile.n_neurons} if self.profile.n_neurons!=50 else {}),
                'engine':self.engine.state_dict(), 'position':self.position, 'goal':self.goal,
                'episode_start':self.episode_start, 'episode_steps':self.episode_steps, 'done':self.done,
                'records':copy.deepcopy(self.records), 'episodes':copy.deepcopy(self.episodes),
                **{name:copy.deepcopy(getattr(self,name).bit_generator.state) for name in ('world_rng','policy_rng','feedback_rng')}}

    def checkpoint(self):
        payload = self.state_dict()
        canonical = json.dumps(payload, sort_keys=True, separators=(',',':'), allow_nan=False).encode()
        return json.dumps({'format':'synapse-arena-checkpoint-v1', 'sha256':hashlib.sha256(canonical).hexdigest(),
                           'payload':payload}, separators=(',',':'), allow_nan=False).encode()

    @classmethod
    def from_checkpoint(cls, data):
        if not isinstance(data, bytes) or len(data) > 10*1024*1024: raise ValueError('arena checkpoint limit is 10 MiB')
        try:
            outer = json.loads(data)
            state = outer['payload']
            canonical = json.dumps(state, sort_keys=True, separators=(',',':'), allow_nan=False).encode()
            if outer['format'] != 'synapse-arena-checkpoint-v1' or hashlib.sha256(canonical).hexdigest() != outer['sha256']:
                raise ValueError('checkpoint integrity check failed')
            if state['format'] != 'synapse-arena-session-v1': raise ValueError('unsupported arena format')
            obj = cls(state['seed'], world=World.from_dict(state['world']), mode=state['mode'], n_neurons=state.get('neurons',50))
            engine = ContinuingNetwork.from_state_dict(state['engine'])
            if (engine.network != obj.engine.network or engine.selected != obj.engine.selected or
                engine.reward_parameters != obj.engine.reward_parameters or engine.dt_ms != .5):
                raise ValueError('checkpoint circuit differs from its seeded arena profile')
            rows, episodes = state['records'], state['episodes']
            if not isinstance(rows, list) or len(rows) > MAX_MOVES or not isinstance(episodes, list): raise ValueError('invalid history')
            if engine.tick != len(rows)*200: raise ValueError('checkpoint is not at a move boundary')
            completed = []; previous = None; group = []
            for i, row in enumerate(rows):
                before, goal = cell(row['before']), cell(row['goal'])
                if before not in obj.world.safe_cells or goal not in obj.world.safe_cells or before == goal:
                    raise ValueError('invalid recorded start or goal')
                expected_step = 1 if previous is None or previous['terminal'] else previous['step']+1
                if row['move'] != i or row['episode'] != len(completed) or row['step'] != expected_step:
                    raise ValueError('invalid move sequence')
                if expected_step > 1 and (row['before'] != previous['after'] or row['goal'] != previous['goal']):
                    raise ValueError('discontinuous journey')
                expected = transition(obj.world, before, goal, row['action'], row['step'])
                if any(row[k] != v for k,v in expected.items()) or row['time_start_ms'] != i*100:
                    raise ValueError('history differs from environment transition')
                if row['observation'] != observe(obj.world,before,goal).tolist(): raise ValueError('invalid recorded observations')
                for name in ('scores_mV','probabilities'):
                    values = np.asarray(row[name], dtype=float)
                    if values.shape != (4,) or not np.isfinite(values).all(): raise ValueError('invalid action display history')
                if type(row['frozen']) is not bool or not math.isfinite(row['update_l2_nA']) or row['update_l2_nA'] < 0:
                    raise ValueError('invalid learning history')
                if not math.isfinite(row['delivered_feedback']) or not -1 <= row['delivered_feedback'] <= 1:
                    raise ValueError('invalid feedback history')
                scores = np.asarray(row['scores_mV'])
                expected_probs = probabilities(scores)
                if row['frozen']:
                    tied = scores == scores.max(); expected_probs = tied.astype(float)/tied.sum()
                if not np.allclose(row['probabilities'],expected_probs,atol=1e-12,rtol=0) or expected_probs[row['action']] <= 0:
                    raise ValueError('action probabilities differ from declared readout')
                if (row['frozen'] or obj.mode == 'learning_disabled') and row['update_l2_nA'] != 0:
                    raise ValueError('frozen/disabled history contains learning')
                if (obj.mode != 'random_feedback' or row['frozen']) and row['delivered_feedback'] != row['reward']:
                    raise ValueError('delivered feedback differs from mode')
                group.append(row)
                if row['terminal']:
                    completed.append({'episode':len(completed),'start':group[0]['before'],'goal':row['goal'],
                        'steps':len(group),'success':row['success'],'hazard':row['hazard'],
                        'collisions':sum(r['collision'] for r in group),'return':float(sum(r['reward'] for r in group))})
                    group = []
                previous = row
            if episodes != completed: raise ValueError('episode summaries differ from history')
            if type(state['done']) is not bool or type(state['episode_steps']) is not int: raise ValueError('invalid episode state')
            if state['position'] is not None and state['episode_steps'] == 0:
                if (cell(state['position']) not in obj.world.safe_cells or cell(state['goal']) not in obj.world.safe_cells
                    or state['position'] == state['goal'] or state['done'] or state['position'] != state['episode_start']
                    or (rows and not rows[-1]['terminal'])):
                    raise ValueError('invalid initial episode')
            elif rows:
                if (list(cell(state['position'])) != rows[-1]['after'] or list(cell(state['goal'])) != rows[-1]['goal'] or
                    state['done'] != rows[-1]['terminal'] or state['episode_steps'] != rows[-1]['step']):
                    raise ValueError('current world differs from final move')
                start_index = len(rows)-state['episode_steps']
                if list(cell(state['episode_start'])) != rows[start_index]['before']: raise ValueError('invalid episode origin')
            elif state['goal'] is not None or state['episode_start'] is not None or not state['done'] or state['episode_steps'] != 0: raise ValueError('invalid empty arena')
            for name in ('world_rng','policy_rng','feedback_rng'):
                if state[name]['bit_generator'] != 'PCG64': raise ValueError('unsupported random generator')
                getattr(obj,name).bit_generator.state = copy.deepcopy(state[name])
            obj.engine = engine
            obj.position = cell(state['position']) if state['position'] is not None else None
            obj.goal = cell(state['goal']) if state['goal'] is not None else None
            obj.episode_start = cell(state['episode_start']) if state['episode_start'] is not None else None
            obj.episode_steps, obj.done = state['episode_steps'], state['done']
            obj.records, obj.episodes = copy.deepcopy(rows), copy.deepcopy(episodes)
            return obj
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError, IndexError) as exc:
            raise ValueError(f'invalid arena checkpoint: {exc}') from exc


def scenarios(world, count=24, seed=10007, excluded=()):
    if type(count) is not int or not 4 <= count <= 40 or type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('evaluation uses 4..40 cases and a uint32 seed')
    excluded = set((cell(s),cell(g)) for s,g in excluded)
    pairs = [(s,g) for s in world.safe_cells for g in world.safe_cells
             if 2 <= abs(s[0]-g[0])+abs(s[1]-g[1]) <= 4 and held_out_pair(s,g) and (s,g) not in excluded]
    if not pairs: raise ValueError('map has no evaluation pairs at distances 2..4')
    rng = np.random.default_rng(seed)
    return [pairs[int(i)] for i in rng.choice(len(pairs),size=count,replace=len(pairs)<count)]


def evaluate(session, cases=None, *, controller='neural', reset_weights=False, seed=10007, world=None):
    if controller not in ('neural','random','greedy') or type(reset_weights) is not bool:
        raise ValueError('unsupported evaluation controller')
    world = world if world is not None else session.world
    if not isinstance(world,World): raise ValueError('evaluation world must be World')
    cases = scenarios(world,seed=seed,excluded=[(r['before'],r['goal']) for r in session.records if r['step']==1 and not r['frozen']]) if cases is None else cases
    if not isinstance(cases,(list,tuple)) or not 1 <= len(cases) <= 40: raise ValueError('one to forty evaluation cases required')
    for start,goal in cases:
        if cell(start) not in world.safe_cells or cell(goal) not in world.safe_cells or cell(start)==cell(goal):
            raise ValueError('evaluation requires distinct safe cells')
    probe = ArenaSession(session.seed,world=world,mode='learning_disabled',n_neurons=session.profile.n_neurons)
    probe.engine.weights[:] = session.initial_weights if reset_weights else session.engine.weights
    rng = np.random.default_rng(seed)
    journeys = []
    for start,goal in cases:
        probe.begin_episode(cell(start),cell(goal))
        path = [list(start)]; rows = []
        if controller == 'neural':
            while not probe.done:
                row,_ = probe.step(frozen=True)
                rows.append(row); path.append(row['after'])
            summary = probe.episodes[-1]
        else:
            position = cell(start)
            for step in range(1,world.max_steps+1):
                obs = observe(world,position,goal)
                options = np.flatnonzero((obs[:4] > 0) & (obs[4:] == 0))
                if not len(options): options = np.flatnonzero(obs[4:] == 0)
                action = int(rng.integers(4)) if controller == 'random' else int(rng.choice(options)) if len(options) else int(rng.integers(4))
                result = transition(world,position,goal,action,step)
                rows.append({'action':action,**result}); position = tuple(result['after']); path.append(list(position))
                if result['terminal']: break
            probe.done = True
            summary = {'steps':len(rows),'success':rows[-1]['success'],'hazard':rows[-1]['hazard'],
                       'collisions':sum(r['collision'] for r in rows),'return':float(sum(r['reward'] for r in rows))}
        journeys.append({'start':list(start),'goal':list(goal),'path':path,'actions':[r['action'] for r in rows],**summary})
    return {'controller':controller,'reset_weights':reset_weights,'cases':len(cases),
            'unique_pairs':len(set((cell(s),cell(g)) for s,g in cases)),
            'successes':sum(j['success'] for j in journeys),
            'success_rate':float(np.mean([j['success'] for j in journeys])),
            'mean_steps':float(np.mean([j['steps'] for j in journeys])),
            'collisions':sum(j['collisions'] for j in journeys),
            'hazard_endings':sum(j['hazard'] for j in journeys), 'journeys':journeys,
            'frozen_weights_unchanged':bool(np.array_equal(probe.engine.weights,session.initial_weights if reset_weights else session.engine.weights))}


def compare(session, count=24, seed=10007, world=None):
    world = world if world is not None else session.world
    cases = scenarios(world,count,seed,[(r['before'],r['goal']) for r in session.records if r['step']==1 and not r['frozen']])
    return {'format':'synapse-arena-evaluation-v1','world':asdict(world),'training_world':asdict(session.world),'training_seed':session.seed,
            'source_condition':session.mode,'source_weights_nA':session.engine.weights.tolist(),
            'source_weight_sha256':hashlib.sha256(session.engine.weights.astype('<f8').tobytes()).hexdigest(),
            'training_moves':len(session.records),'training_episodes':len(session.episodes),
            'evaluation_seed':seed,'policy':'Frozen greedy neural scores; no exploration or weight updates.',
            'pair_partition':'Fixed reserved start/goal pairs, distance 2..4; manually trained pairs excluded.',
            'conditions':{'trained':evaluate(session,cases,seed=seed,world=world),
                          'reset_weights':evaluate(session,cases,reset_weights=True,seed=seed,world=world),
                          'random':evaluate(session,cases,controller='random',seed=seed,world=world),
                          'greedy_sensors':evaluate(session,cases,controller='greedy',seed=seed,world=world)}}


def study(seeds=(7,19,43), training_episodes=100, evaluation_cases=24, world=None):
    if (not isinstance(seeds,(tuple,list)) or not 1 <= len(seeds) <= 5 or len(set(seeds)) != len(seeds)
        or type(training_episodes) is not int or not 20 <= training_episodes <= 120):
        raise ValueError('study uses 1..5 unique seeds and 20..120 training episodes')
    world = world if world is not None else World()
    cases = scenarios(world,evaluation_cases)
    runs = []
    for seed in seeds:
        conditions = {}; starts = []
        for mode in MODES:
            session = ArenaSession(seed,world=world,mode=mode)
            for batch in range(0,training_episodes,20): session.train(min(20,training_episodes-batch))
            result = evaluate(session,cases)
            starts.append([(e['start'],e['goal']) for e in session.episodes])
            conditions[mode] = {'training_moves':len(session.records), 'evaluation':result,
                                'weights_changed':int(np.count_nonzero(session.engine.weights != session.initial_weights))}
            if mode == 'learning':
                conditions['reset_weights'] = {'evaluation':evaluate(session,cases,reset_weights=True)}
                conditions['random'] = {'evaluation':evaluate(session,cases,controller='random')}
                conditions['greedy_sensors'] = {'evaluation':evaluate(session,cases,controller='greedy')}
        if not starts[0] == starts[1] == starts[2]: raise RuntimeError('matched curriculum pair stream diverged')
        runs.append({'seed':seed,'conditions':conditions})
    return {'format':'synapse-arena-study-v1','world':asdict(world), 'training_episodes':training_episodes,
            'evaluation_cases':evaluation_cases,'evaluation_seed':10007,
            'protocol':'Matched initial wiring and curriculum pair stream per seed; reserved pairs; frozen greedy evaluation.',
            'runs':runs}
