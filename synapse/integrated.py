"""A 50-cell continuing circuit in a two-choice reversal environment.

The circuit receives cue currents and scalar feedback, never a desired action.
Action decoding/exploration and action-execution currents are explicit controller
components; this is an engineered neural controller, not a biological brain model.
"""

from dataclasses import asdict, dataclass
import copy
import math
import numpy as np

from .continuing import ContinuingNetwork, RewardParameters
from .network import Network, Synapse

MODES = ('learning', 'learning_disabled', 'random_feedback')
DEFAULT_INTEGRATED_SEEDS = (7, 19, 43)
GROUPS = {'sensory_A': tuple(range(0, 5)), 'sensory_B': tuple(range(5, 10)),
          'association_A': tuple(range(10, 20)), 'association_B': tuple(range(20, 30)),
          'inhibitory_A': tuple(range(30, 35)), 'inhibitory_B': tuple(range(35, 40)),
          'action_0': tuple(range(40, 45)), 'action_1': tuple(range(45, 50))}


@dataclass(frozen=True)
class IntegratedConfig:
    dt_ms: float = 0.2
    reversal_trial: int = 100
    session_limit: int = 1000
    exploration: float = 0.2
    temperature_mV: float = 0.7

    def __post_init__(self):
        if self.dt_ms not in (0.1, 0.2):
            raise ValueError('integrated time step must be 0.1 or 0.2 ms')
        if type(self.reversal_trial) is not int or not 20 <= self.reversal_trial <= 400:
            raise ValueError('reversal_trial must be an integer from 20 to 400')
        if type(self.session_limit) is not int or not self.reversal_trial < self.session_limit <= 1000:
            raise ValueError('session_limit must exceed reversal_trial and be <= 1000')
        if not math.isfinite(self.exploration) or not 0 <= self.exploration <= 1:
            raise ValueError('exploration must lie in [0, 1]')
        if not math.isfinite(self.temperature_mV) or self.temperature_mV <= 0:
            raise ValueError('temperature_mV must be positive')


def build_integrated_network(rng):
    edges, selected, pairs = [], [], set()
    def add(source, target, weight, *, plastic=False):
        if (source, target) in pairs:
            raise ValueError('duplicate circuit connection')
        pairs.add((source, target))
        if plastic:
            selected.append(len(edges))
        edges.append(Synapse(source, target, float(weight), 1.0))
    for cue in (0, 1):
        sensory = range(5*cue, 5*cue+5)
        association = range(10+10*cue, 20+10*cue)
        inhibitory = range(30+5*cue, 35+5*cue)
        for source in sensory:
            for target in association:
                add(source, target, 0.25)
        for k, source in enumerate(association):
            for offset in (1, 2):
                add(source, 10+10*cue+(k+offset)%10, 0.03)
            add(source, 10+10*(1-cue)+k, 0.005)
            for target in inhibitory:
                add(source, target, 0.12)
        for source in inhibitory:
            for target in association:
                add(source, target, -0.04)
            for target in range(40, 50):
                add(source, target, -0.002)
    for source in range(10, 30):
        for target in range(40, 50):
            add(source, target, np.clip(rng.normal(0.025, 0.0005), 0.023, 0.027), plastic=True)
    for source in range(40, 50):
        k = source-40
        add(source, 10+k, 0.008)
        add(source, 20+k, 0.008)
        add(source, 30+k, 0.02)
    return Network(50, tuple(edges), inhibitory_neurons=tuple(range(30, 40))), tuple(selected)


def action_probabilities(scores_mV, config):
    scores = np.asarray(scores_mV, dtype=float)
    if scores.shape != (2,) or not np.isfinite(scores).all():
        raise ValueError('two finite action scores are required')
    logit = float(np.clip((scores[1]-scores[0])/config.temperature_mV, -60, 60))
    p1 = 1/(1+math.exp(-logit))
    p1 = config.exploration/2 + (1-config.exploration)*p1
    return np.array([1-p1, p1])


def environment_outcome(cue, action, trial, reversal_trial):
    if cue not in (0, 1) or action not in (0, 1):
        raise ValueError('cue and action must be binary')
    correct_action = int(cue) if trial < reversal_trial else 1-int(cue)
    return int(action == correct_action)


class IntegratedSession:
    def __init__(self, seed=7, *, mode='learning', config=None):
        if type(seed) is not int or not 0 <= seed < 2**32:
            raise ValueError('seed must be an integer in [0, 2**32)')
        if mode not in MODES:
            raise ValueError('unsupported integrated condition')
        self.seed, self.mode = seed, mode
        self.config = config if config is not None else IntegratedConfig()
        if not isinstance(self.config, IntegratedConfig):
            raise ValueError('config must be IntegratedConfig')
        children = np.random.SeedSequence(seed).spawn(4)
        network_rng, self.cue_rng, self.policy_rng, self.feedback_rng = [np.random.default_rng(s) for s in children]
        network, selected = build_integrated_network(network_rng)
        self.engine = ContinuingNetwork(network, dt_ms=self.config.dt_ms, eligible_synapses=selected)
        self.trial_index = 0
        self.cue_buffer = []
        self.records = []

    def step_trial(self, *, record=False):
        if self.trial_index >= self.config.session_limit:
            raise ValueError('integrated session reached its trial budget')
        if not self.cue_buffer:
            self.cue_buffer = self.cue_rng.permutation([0]*10+[1]*10).astype(int).tolist()
        cue = self.cue_buffer.pop(0)
        start_time = self.engine.time_ms
        blocks = []
        def advance(duration, current=0.0):
            block = self.engine.advance(duration, current, record=record)
            if record:
                blocks.append(block)
        sensory = np.zeros(50)
        sensory[list(GROUPS['sensory_A' if cue == 0 else 'sensory_B'])] = 0.8
        advance(5, sensory)
        advance(20)
        # Read actual state before outcome or action-execution input is available.
        scores = np.array([self.engine.voltage[list(GROUPS[f'action_{i}'])].mean()-self.engine.network.neuron.rest_mV for i in (0, 1)])
        probabilities = action_probabilities(scores, self.config)
        action = int(self.policy_rng.random() >= probabilities[0])
        motor = np.zeros(50)
        motor[list(GROUPS[f'action_{action}'])] = 0.8
        # This executes the ALREADY selected action, not the environment's answer.
        advance(5, motor)
        advance(5)
        reward = environment_outcome(cue, action, self.trial_index, self.config.reversal_trial)
        feedback = float(self.feedback_rng.integers(0, 2)) if self.mode == 'random_feedback' else float(reward)
        change = self.engine.feedback(feedback, learning_enabled=self.mode != 'learning_disabled')
        advance(65)
        weights = self.engine.weights[list(self.engine.selected)].reshape(20, 10)
        preferences = [float(weights[:10, :5].mean()), float(weights[:10, 5:].mean()),
                       float(weights[10:, :5].mean()), float(weights[10:, 5:].mean())]
        row = {'trial': self.trial_index, 'time_start_ms': start_time, 'time_end_ms': self.engine.time_ms,
               'cue': cue, 'phase': int(self.trial_index >= self.config.reversal_trial), 'action': action,
               'reward': reward, 'delivered_feedback': feedback, 'action_scores_mV': scores.tolist(),
               'action_probabilities': probabilities.tolist(), 'greedy_action': int(scores[1] > scores[0]),
               'greedy_correct': environment_outcome(cue, int(scores[1] > scores[0]), self.trial_index, self.config.reversal_trial),
               'weight_preferences_nA': preferences, 'update_l2_nA': float(np.linalg.norm(change))}
        self.records.append(row)
        self.trial_index += 1
        return dict(row), tuple(blocks)

    def state_dict(self):
        return {'format': 'synapse-integrated-session-v1', 'seed': self.seed, 'mode': self.mode,
                'configuration': asdict(self.config), 'trial_index': self.trial_index,
                'engine': self.engine.state_dict(), 'cue_buffer': list(self.cue_buffer),
                'cue_rng': copy.deepcopy(self.cue_rng.bit_generator.state),
                'policy_rng': copy.deepcopy(self.policy_rng.bit_generator.state),
                'feedback_rng': copy.deepcopy(self.feedback_rng.bit_generator.state),
                'records': copy.deepcopy(self.records)}

    @classmethod
    def from_state_dict(cls, state):
        if not isinstance(state, dict) or state.get('format') != 'synapse-integrated-session-v1':
            raise ValueError('unsupported integrated session format')
        try:
            obj = cls(state['seed'], mode=state['mode'], config=IntegratedConfig(**state['configuration']))
            engine = ContinuingNetwork.from_state_dict(state['engine'])
            if engine.network != obj.engine.network or engine.selected != obj.engine.selected or engine.reward_parameters != obj.engine.reward_parameters:
                raise ValueError('checkpoint circuit does not match its seeded profile')
            trial = state['trial_index']
            ticks_per_trial = round(100/obj.config.dt_ms)
            if type(trial) is not int or not 0 <= trial <= obj.config.session_limit or engine.tick != trial*ticks_per_trial:
                raise ValueError('session checkpoints must be at a complete trial boundary')
            if engine.dt_ms != obj.config.dt_ms:
                raise ValueError('checkpoint time step mismatch')
            buffer = state['cue_buffer']
            if not isinstance(buffer, list) or len(buffer) > 20 or any(type(c) is not int or c not in (0, 1) for c in buffer):
                raise ValueError('invalid cue buffer')
            records = state['records']
            if not isinstance(records, list) or len(records) != trial:
                raise ValueError('checkpoint history/trial count mismatch')
            for i, row in enumerate(records):
                if row['trial'] != i or row['cue'] not in (0, 1) or row['action'] not in (0, 1):
                    raise ValueError('invalid trial history')
                if row['reward'] != environment_outcome(row['cue'], row['action'], i, obj.config.reversal_trial):
                    raise ValueError('trial reward is inconsistent with the environment')
            for name in ('cue_rng', 'policy_rng', 'feedback_rng'):
                if state[name]['bit_generator'] != 'PCG64':
                    raise ValueError('unsupported random generator in checkpoint')
                getattr(obj, name).bit_generator.state = copy.deepcopy(state[name])
            obj.engine, obj.trial_index = engine, trial
            obj.cue_buffer, obj.records = list(buffer), copy.deepcopy(records)
            return obj
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f'invalid integrated checkpoint: {exc}') from exc


def session_metrics(records, reversal_trial, window=20):
    if len(records) < reversal_trial+window or reversal_trial < window:
        raise ValueError('enough trials on both sides of reversal are required')
    def mean(start, stop, key='reward'):
        return float(np.mean([r[key] for r in records[start:stop]]))
    return {'initial_window_accuracy': mean(0, window),
            'before_reversal_accuracy': mean(reversal_trial-window, reversal_trial),
            'after_reversal_accuracy': mean(reversal_trial, reversal_trial+window),
            'final_window_accuracy': mean(len(records)-window, len(records)),
            'overall_accuracy': mean(0, len(records)),
            'final_greedy_accuracy': mean(len(records)-window, len(records), 'greedy_correct'),
            'window_trials': window}
