"""Continuing LIF circuit with explicit state and reward-gated eligibility.

Unlike batch experiments, advance() retains voltages, currents, refractory
counters, pending delayed events and learning traces. No plotting/UI dependency.
"""

from dataclasses import asdict, dataclass
from contextlib import contextmanager
import math
import numpy as np

from .lif import LIFParameters, step_count
from .network import Network, Synapse, _decay_coefficients, MAX_TRACE_VALUES, MAX_SPIKES

MAX_PENDING_EVENTS = 200_000
MAX_TOTAL_TICKS = 10_000_000


@dataclass(frozen=True)
class RewardParameters:
    learning_rate_nA: float = 0.015
    tau_pre_ms: float = 20.0
    tau_post_ms: float = 20.0
    tau_eligibility_ms: float = 150.0
    depression_ratio: float = 1.05
    reference_reward: float = 0.5
    w_min_nA: float = 0.002
    w_max_nA: float = 0.06

    def __post_init__(self):
        if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in asdict(self).values()):
            raise ValueError('reward parameters must be finite numbers')
        if self.learning_rate_nA <= 0 or min(self.tau_pre_ms, self.tau_post_ms, self.tau_eligibility_ms) <= 0:
            raise ValueError('learning rate and time constants must be positive')
        if self.depression_ratio < 0 or not 0 <= self.reference_reward <= 1:
            raise ValueError('invalid depression ratio or reference reward')
        if not 0 <= self.w_min_nA < self.w_max_nA:
            raise ValueError('invalid reward weight bounds')


class RewardEligibility:
    """Three-factor engineering rule: timing eligibility times centred reward.

    Pre/post traces and eligibility are dimensionless. Eligibility is consumed
    after each outcome; pre/post traces and all neural states remain intact.
    """
    def __init__(self, size, parameters=None):
        if type(size) is not int or not 0 <= size <= 10_000:
            raise ValueError('eligibility size is invalid')
        self.parameters = parameters if parameters is not None else RewardParameters()
        if not isinstance(self.parameters, RewardParameters):
            raise ValueError('parameters must be RewardParameters')
        self.pre = np.zeros(size)
        self.post = np.zeros(size)
        self.eligibility = np.zeros(size)
        self.last_time_ms = 0.0
        self.last_event_time_ms = -1.0

    def decay_to(self, time_ms):
        if not math.isfinite(time_ms) or time_ms < self.last_time_ms:
            raise ValueError('eligibility time must be finite and nondecreasing')
        elapsed = time_ms - self.last_time_ms
        p = self.parameters
        self.pre *= math.exp(-elapsed / p.tau_pre_ms)
        self.post *= math.exp(-elapsed / p.tau_post_ms)
        self.eligibility *= math.exp(-elapsed / p.tau_eligibility_ms)
        self.last_time_ms = float(time_ms)

    def observe(self, time_ms, pre_indices=(), post_indices=()):
        if time_ms <= self.last_event_time_ms:
            raise ValueError('combine simultaneous eligibility events in one call')
        def indices(values):
            values = tuple(values)
            if any(not isinstance(i, (int, np.integer)) or isinstance(i, (bool, np.bool_)) for i in values):
                raise ValueError('event indices must be integers')
            result = np.array(values, dtype=np.int64)
            if len(set(values)) != len(values) or np.any(result < 0) or np.any(result >= len(self.pre)):
                raise ValueError('event indices must be unique and in range')
            return result
        pre, post = indices(pre_indices), indices(post_indices)
        self.decay_to(time_ms)
        # Both directions use the old traces, excluding new zero-lag pairs.
        self.eligibility[pre] -= self.parameters.depression_ratio * self.post[pre]
        self.eligibility[post] += self.pre[post]
        self.pre[pre] += 1
        self.post[post] += 1
        self.last_event_time_ms = float(time_ms)

    def feedback(self, time_ms, reward, weights, *, learning_enabled=True):
        if not isinstance(reward, (int, float, np.integer, np.floating)) or not math.isfinite(reward) or not 0 <= reward <= 1:
            raise ValueError('reward must be a finite value in [0, 1]')
        if type(learning_enabled) is not bool:
            raise ValueError('learning_enabled must be a boolean')
        values = np.asarray(weights, dtype=float)
        if values.shape != self.pre.shape or not np.isfinite(values).all():
            raise ValueError('one finite weight per eligible connection is required')
        p = self.parameters
        if np.any(values < p.w_min_nA) or np.any(values > p.w_max_nA):
            raise ValueError('eligible weights are outside their bounds')
        self.decay_to(time_ms)
        if learning_enabled:
            with np.errstate(over='raise', invalid='raise'):
                try:
                    updated = values + p.learning_rate_nA * (float(reward)-p.reference_reward) * self.eligibility
                except FloatingPointError as exc:
                    raise ValueError('reward update overflowed') from exc
            updated = np.clip(updated, p.w_min_nA, p.w_max_nA)
        else:
            updated = values.copy()
        self.eligibility.fill(0)
        return updated

    def state_dict(self):
        return {'pre': self.pre.tolist(), 'post': self.post.tolist(),
                'eligibility': self.eligibility.tolist(), 'last_time_ms': self.last_time_ms,
                'last_event_time_ms': self.last_event_time_ms}


@dataclass(frozen=True)
class ContinuingBlock:
    spike_counts: np.ndarray
    spike_times_ms: np.ndarray
    spike_neurons: np.ndarray
    time_ms: np.ndarray | None = None
    voltage_mV: np.ndarray | None = None
    synaptic_current_nA: np.ndarray | None = None


class ContinuingNetwork:
    """State at an absolute time tick, before or after its explicit boundary.

    A step processes arrivals/previous endpoint spikes, evolves one interval,
    then keeps new endpoint spikes for the next boundary. settle() is idempotent.
    """
    def __init__(self, network, *, dt_ms=0.2, eligible_synapses=(), reward_parameters=None):
        if not isinstance(network, Network):
            raise ValueError('network must be Network')
        if not math.isfinite(dt_ms) or dt_ms <= 0:
            raise ValueError('dt_ms must be positive and finite')
        self.network, self.dt_ms = network, float(dt_ms)
        self.reward_parameters = reward_parameters if reward_parameters is not None else RewardParameters()
        self.selected = tuple(eligible_synapses)
        if any(type(i) is not int or not 0 <= i < len(network.synapses) for i in self.selected) or len(set(self.selected)) != len(self.selected):
            raise ValueError('invalid eligible synapse indices')
        self.weights = np.array([s.weight_nA for s in network.synapses], dtype=float)
        if any(network.synapses[i].weight_nA <= 0 for i in self.selected):
            raise ValueError('only excitatory connections can use reward learning')
        p = self.reward_parameters
        if self.selected and (np.any(self.weights[list(self.selected)] < p.w_min_nA) or np.any(self.weights[list(self.selected)] > p.w_max_nA)):
            raise ValueError('initial eligible weights are outside reward bounds')
        self.rule = RewardEligibility(len(self.selected), p)
        self.local_index = np.full(len(self.weights), -1, dtype=np.int64)
        self.local_index[list(self.selected)] = np.arange(len(self.selected))
        self.targets = np.array([s.target for s in network.synapses], dtype=np.int64)
        self.plastic_targets = self.targets[list(self.selected)]
        self.outgoing = [[] for _ in range(network.n_neurons)]
        self.delays = []
        for i, edge in enumerate(network.synapses):
            ratio = edge.delay_ms / self.dt_ms
            if not math.isfinite(ratio) or ratio > MAX_TOTAL_TICKS:
                raise ValueError('delay exceeds the continuing-engine limit')
            delay = round(ratio)
            if delay < 1 or not math.isclose(ratio, delay, rel_tol=0, abs_tol=1e-7):
                raise ValueError('delays must be >= dt and align to the time grid')
            self.delays.append(delay)
            self.outgoing[edge.source].append(i)
        self.voltage = np.full(network.n_neurons, network.neuron.rest_mV)
        self.synaptic = np.zeros(network.n_neurons)
        self.remaining = np.zeros(network.n_neurons, dtype=np.int64)
        self.previous_fired = np.empty(0, dtype=np.int64)
        self.pending = {}
        self.pending_count = 0
        self.tick = 0
        self.settled = False
        self.last_reward_tick = -1
        self.total_spikes = np.zeros(network.n_neurons, dtype=np.int64)
        self._transmission_sink = None
        self._transmission_gains = None
        self.m_decay, self.s_decay, self.coupling = _decay_coefficients(self.dt_ms, network.neuron.tau_ms, network.synaptic_tau_ms)
        self.fraction = -math.expm1(-self.dt_ms/network.neuron.tau_ms)
        ratio = network.neuron.refractory_ms / self.dt_ms
        if not math.isfinite(ratio) or ratio > MAX_TOTAL_TICKS:
            raise ValueError('refractory duration exceeds continuing-engine limit')
        nearest = round(ratio)
        self.ref_steps = nearest if math.isclose(ratio, nearest, rel_tol=0, abs_tol=1e-9) else math.ceil(ratio)

    @property
    def time_ms(self):
        return self.tick * self.dt_ms

    @contextmanager
    def record_transmissions(self):
        """Observe processed arrivals, including feedback boundaries, without settling.

        Each tuple is (arrival time, global edge index, transmitted weight).
        This temporary observer is not physical state and is not checkpointed.
        """
        if self._transmission_sink is not None:
            raise ValueError('transmission recording is already active')
        events=[]
        self._transmission_sink=events
        try:
            yield events
        finally:
            self._transmission_sink=None

    @contextmanager
    def temporary_transmission_gains(self, gains):
        """Frozen-probe control: scale future arrivals without changing weights.

        Zero blocks a transmission, including an already queued arrival.
        Previously delivered current continues decaying. No feedback or snapshot
        is allowed while this temporary physical control is active.
        """
        if self._transmission_gains is not None:
            raise ValueError('transmission controls are already active')
        values=np.asarray(gains,dtype=float)
        if values.shape!=self.weights.shape or not np.isfinite(values).all() or np.any(values<0) or np.any(values>4):
            raise ValueError('one finite transmission gain in [0,4] is required per connection')
        self._transmission_gains=values.copy()
        try:
            yield
        finally:
            self._transmission_gains=None

    def settle(self):
        if self.settled:
            return
        arrivals = self.pending.get(self.tick, [])
        if self._transmission_sink is not None and len(self._transmission_sink)+len(arrivals)>MAX_PENDING_EVENTS:
            raise ValueError('transmission recording exceeds its event budget')
        self.pending.pop(self.tick, None)
        self.pending_count -= len(arrivals)
        if self._transmission_gains is not None:
            arrivals=[i for i in arrivals if self._transmission_gains[i]>0]
        if arrivals:
            delivered=self.weights[arrivals]
            if self._transmission_gains is not None:
                delivered=delivered*self._transmission_gains[arrivals]
            if self._transmission_sink is not None:
                self._transmission_sink.extend((self.time_ms,int(i),float(w)) for i,w in zip(arrivals,delivered))
            with np.errstate(over='raise', invalid='raise'):
                try:
                    np.add.at(self.synaptic, self.targets[arrivals], delivered)
                except FloatingPointError as exc:
                    raise ValueError('pending arrival current overflowed') from exc
        if self.selected:
            pre = [int(self.local_index[i]) for i in arrivals if self.local_index[i] >= 0]
            post = np.flatnonzero(np.isin(self.plastic_targets, self.previous_fired))
            if pre or len(post):
                self.rule.observe(self.time_ms, pre, post)
        self.previous_fired = np.empty(0, dtype=np.int64)
        self.settled = True

    def advance(self, duration_ms, current_nA=0.0, *, record=False):
        if type(record) is not bool:
            raise ValueError('record must be a boolean')
        steps = step_count(duration_ms, self.dt_ms)
        n, p = self.network.n_neurons, self.network.neuron
        if self.tick + steps > MAX_TOTAL_TICKS:
            raise ValueError('continuing session exceeds its tick budget')
        if record and (steps + 1) * n > MAX_TRACE_VALUES:
            raise ValueError('block recording exceeds the trace limit')
        raw = np.asarray(current_nA, dtype=float)
        try:
            current = np.broadcast_to(raw, (steps, n))
        except ValueError as exc:
            raise ValueError('current must be scalar, one value per neuron, or (steps,N)') from exc
        if not np.isfinite(current).all():
            raise ValueError('currents must be finite')
        first_tick = self.tick
        voltage = np.empty((steps+1, n)) if record else None
        synaptic = np.empty((steps, n)) if record else None
        if record:
            voltage[0] = self.voltage
        counts = np.zeros(n, dtype=np.int64)
        times, cells = [], []
        with np.errstate(over='raise', invalid='raise'):
            try:
                for i in range(steps):
                    self.settle()
                    if record:
                        synaptic[i] = self.synaptic
                    clamped = self.remaining > 0
                    self.remaining[clamped] -= 1
                    equilibrium = p.rest_mV + p.resistance_MOhm * current[i]
                    candidate = self.m_decay*self.voltage + self.fraction*equilibrium + p.resistance_MOhm*self.coupling*self.synaptic
                    candidate[clamped] = p.reset_mV
                    fired = np.flatnonzero((~clamped) & (candidate >= p.threshold_mV))
                    candidate[fired] = p.reset_mV
                    self.voltage = candidate
                    self.remaining[fired] = self.ref_steps
                    self.tick += 1
                    self.previous_fired = fired
                    self.settled = False
                    self.synaptic *= self.s_decay
                    self.total_spikes[fired] += 1
                    counts[fired] += 1
                    for cell in fired:
                        times.append(self.time_ms)
                        cells.append(int(cell))
                        if len(times) > MAX_SPIKES:
                            raise ValueError('block exceeds the spike-event budget')
                        for edge in self.outgoing[cell]:
                            self.pending_count += 1
                            if self.pending_count > MAX_PENDING_EVENTS:
                                raise ValueError('pending arrivals exceed the queue budget')
                            arrival = self.tick + self.delays[edge]
                            self.pending.setdefault(arrival, []).append(edge)
                    if record:
                        voltage[i+1] = self.voltage
            except FloatingPointError as exc:
                raise ValueError('continuing circuit overflowed; reduce inputs/weights') from exc
        result_times = (np.arange(first_tick, self.tick+1)*self.dt_ms) if record else None
        arrays = (counts, np.array(times, dtype=float), np.array(cells, dtype=np.int64), result_times, voltage, synaptic)
        for a in arrays:
            if a is not None:
                a.flags.writeable = False
        return ContinuingBlock(*arrays)

    def feedback(self, reward, *, learning_enabled=True):
        # Validate first, so rejected calls do not consume a boundary or credit.
        if self._transmission_gains is not None:
            raise ValueError('feedback is disabled during a temporary intervention')
        if not isinstance(reward, (int, float, np.integer, np.floating)) or not math.isfinite(reward) or not 0 <= reward <= 1:
            raise ValueError('reward must lie in [0, 1]')
        if type(learning_enabled) is not bool:
            raise ValueError('learning_enabled must be a boolean')
        if self.last_reward_tick == self.tick:
            raise ValueError('feedback already consumed at this tick')
        self.settle()
        selected = list(self.selected)
        before = self.weights[selected].copy()
        self.weights[selected] = self.rule.feedback(self.time_ms, float(reward), before, learning_enabled=learning_enabled)
        self.last_reward_tick = self.tick
        return self.weights[selected] - before

    def state_dict(self):
        """Copy ALL state; this call does not process a boundary or advance time."""
        if self._transmission_gains is not None:
            raise ValueError('finish the temporary intervention before checkpointing')
        return {'format': 'synapse-continuing-v1', 'network': asdict(self.network), 'dt_ms': self.dt_ms,
                'selected': list(self.selected), 'reward_parameters': asdict(self.reward_parameters),
                'weights': self.weights.tolist(), 'voltage': self.voltage.tolist(), 'synaptic': self.synaptic.tolist(),
                'remaining': self.remaining.tolist(), 'previous_fired': self.previous_fired.tolist(),
                'pending': {str(k): list(v) for k, v in self.pending.items()}, 'tick': self.tick,
                'settled': self.settled, 'last_reward_tick': self.last_reward_tick,
                'total_spikes': self.total_spikes.tolist(), 'eligibility': self.rule.state_dict()}

    @classmethod
    def from_state_dict(cls, state):
        if not isinstance(state, dict) or state.get('format') != 'synapse-continuing-v1':
            raise ValueError('unsupported continuing checkpoint format')
        try:
            cfg = state['network']
            network = Network(cfg['n_neurons'], tuple(Synapse(**edge) for edge in cfg['synapses']),
                              tuple(cfg['inhibitory_neurons']), cfg['synaptic_tau_ms'], LIFParameters(**cfg['neuron']))
            obj = cls(network, dt_ms=state['dt_ms'], eligible_synapses=tuple(state['selected']),
                      reward_parameters=RewardParameters(**state['reward_parameters']))
            tick = state['tick']
            if type(tick) is not int or not 0 <= tick <= MAX_TOTAL_TICKS or type(state['settled']) is not bool:
                raise ValueError('invalid checkpoint time/boundary')
            def vector(name, length, *, integer=False):
                raw = state[name]
                if integer and any(type(x) is not int for x in raw):
                    raise ValueError(f'{name} must contain integers')
                a = np.asarray(raw, dtype=np.int64 if integer else float)
                if a.shape != (length,) or not np.isfinite(a).all():
                    raise ValueError(f'invalid checkpoint {name}')
                return a.copy()
            n, m = network.n_neurons, len(network.synapses)
            obj.weights = vector('weights', m)
            obj.voltage = vector('voltage', n)
            obj.synaptic = vector('synaptic', n)
            obj.remaining = vector('remaining', n, integer=True)
            obj.total_spikes = vector('total_spikes', n, integer=True)
            if np.any(obj.voltage >= network.neuron.threshold_mV) or np.any(obj.remaining < 0) or np.any(obj.remaining > obj.ref_steps) or np.any(obj.total_spikes < 0):
                raise ValueError('invalid voltage, refractory or spike-count state')
            selected = set(obj.selected)
            for i, edge in enumerate(network.synapses):
                if i in selected:
                    if not obj.reward_parameters.w_min_nA <= obj.weights[i] <= obj.reward_parameters.w_max_nA:
                        raise ValueError('plastic weight outside bounds')
                elif obj.weights[i] != edge.weight_nA:
                    raise ValueError('fixed connection changed in checkpoint')
            previous = state['previous_fired']
            if len(set(previous)) != len(previous) or any(type(i) is not int or not 0 <= i < n for i in previous):
                raise ValueError('invalid previous spikes')
            if state['settled'] and previous:
                raise ValueError('settled boundary cannot retain previous spikes')
            obj.previous_fired = np.array(previous, dtype=np.int64)
            pending = {}
            for key, edges in state['pending'].items():
                when = int(key)
                if str(when) != key or when < tick or (state['settled'] and when == tick) or when > tick + max(obj.delays, default=1):
                    raise ValueError('invalid pending event time')
                if any(type(i) is not int or not 0 <= i < m for i in edges) or len(set(edges)) != len(edges):
                    raise ValueError('invalid pending synapse events')
                pending[when] = list(edges)
            if sum(map(len, pending.values())) > MAX_PENDING_EVENTS:
                raise ValueError('checkpoint queue exceeds event budget')
            eligibility = state['eligibility']
            for name in ('pre', 'post', 'eligibility'):
                a = np.asarray(eligibility[name], dtype=float)
                if a.shape != (len(obj.selected),) or not np.isfinite(a).all() or (name != 'eligibility' and np.any(a < 0)):
                    raise ValueError('invalid eligibility state')
                setattr(obj.rule, name, a.copy())
            last_time = eligibility['last_time_ms']
            if not isinstance(last_time, (int, float)) or not math.isfinite(last_time) or not 0 <= last_time <= tick*obj.dt_ms:
                raise ValueError('invalid eligibility timestamp')
            last_event = eligibility['last_event_time_ms']
            if not isinstance(last_event, (int, float)) or not math.isfinite(last_event) or not -1 <= last_event <= last_time:
                raise ValueError('invalid eligibility event timestamp')
            last_reward = state['last_reward_tick']
            if type(last_reward) is not int or not -1 <= last_reward <= tick:
                raise ValueError('invalid reward timestamp')
            obj.rule.last_time_ms = float(last_time)
            obj.rule.last_event_time_ms = float(last_event)
            obj.tick, obj.settled, obj.last_reward_tick = tick, state['settled'], last_reward
            obj.pending, obj.pending_count = pending, sum(map(len, pending.values()))
            return obj
        except (KeyError, TypeError, OverflowError, ValueError) as exc:
            raise ValueError(f'invalid continuing checkpoint: {exc}') from exc
