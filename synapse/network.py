"""Delayed current-based LIF circuits, independent of plotting and the interface.

All cells share LIF parameters and one exponential synaptic decay constant.
Weights are current jumps in nA; this is not a conductance-based synapse model.
See docs/NETWORK_MODEL.md for update ordering, units and limits.
"""

from dataclasses import dataclass, field
import math

import numpy as np

from .lif import LIFParameters, step_count
from .plasticity import PairSTDP, STDPParameters

MAX_NEURONS = 200
MAX_SYNAPSES = 10_000
MAX_TRACE_VALUES = 2_000_000
MAX_SPIKES = 200_000
MAX_PENDING_PLASTIC_EVENTS = 200_000


@dataclass(frozen=True)
class Synapse:
    source: int
    target: int
    weight_nA: float
    delay_ms: float = 1.0

    def __post_init__(self):
        for name, value in (("source", self.source), ("target", self.target)):
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if not math.isfinite(self.weight_nA) or self.weight_nA == 0:
            raise ValueError("weight_nA must be finite and nonzero")
        if not math.isfinite(self.delay_ms) or self.delay_ms <= 0:
            raise ValueError("delay_ms must be positive and finite")


@dataclass(frozen=True)
class Network:
    n_neurons: int
    synapses: tuple[Synapse, ...] = ()
    inhibitory_neurons: tuple[int, ...] = ()
    synaptic_tau_ms: float = 5.0
    neuron: LIFParameters = field(default_factory=LIFParameters)

    def __post_init__(self):
        if type(self.n_neurons) is not int or not 1 <= self.n_neurons <= MAX_NEURONS:
            raise ValueError(f"n_neurons must be an integer in [1, {MAX_NEURONS}]")
        if not isinstance(self.neuron, LIFParameters):
            raise ValueError("neuron must be LIFParameters")
        if not math.isfinite(self.synaptic_tau_ms) or self.synaptic_tau_ms <= 0:
            raise ValueError("synaptic_tau_ms must be positive and finite")
        # Freeze caller-provided collections too; execution never mutates configuration.
        object.__setattr__(self, "synapses", tuple(self.synapses))
        object.__setattr__(self, "inhibitory_neurons", tuple(self.inhibitory_neurons))
        if len(self.synapses) > MAX_SYNAPSES:
            raise ValueError(f"at most {MAX_SYNAPSES:,} synapses are supported")
        inhibitory = set(self.inhibitory_neurons)
        if len(inhibitory) != len(self.inhibitory_neurons):
            raise ValueError("inhibitory_neurons must not contain duplicates")
        if any(type(i) is not int or not 0 <= i < self.n_neurons for i in inhibitory):
            raise ValueError("inhibitory neuron indices are invalid")
        seen = set()
        for synapse in self.synapses:
            if not isinstance(synapse, Synapse):
                raise ValueError("each connection must be a Synapse")
            if max(synapse.source, synapse.target) >= self.n_neurons:
                raise ValueError("synapse index is outside this network")
            pair = synapse.source, synapse.target
            if pair in seen:
                raise ValueError("duplicate source-target pairs are not supported")
            seen.add(pair)
            if (synapse.source in inhibitory) != (synapse.weight_nA < 0):
                raise ValueError("all outgoing weights must match their source's E/I type")


@dataclass(frozen=True)
class NetworkResult:
    time_ms: np.ndarray
    voltage_mV: np.ndarray
    external_current_nA: np.ndarray
    synaptic_current_nA: np.ndarray
    spike_times_ms: np.ndarray
    spike_neurons: np.ndarray
    dt_ms: float
    effective_refractory_ms: float
    initial_weights_nA: np.ndarray | None = None
    final_weights_nA: np.ndarray | None = None
    weight_history_nA: np.ndarray | None = None
    plastic_synapse_indices: tuple[int, ...] = ()

    @property
    def spike_counts(self):
        return np.bincount(self.spike_neurons, minlength=self.voltage_mV.shape[1])


def _decay_coefficients(dt, membrane_tau, synaptic_tau):
    """Return exact coupled linear-system coefficients without subtracting decays."""
    membrane_decay = math.exp(-dt / membrane_tau)
    synaptic_decay = math.exp(-dt / synaptic_tau)
    if membrane_tau == synaptic_tau:
        coupling = (dt / membrane_tau) * membrane_decay
    else:
        difference = abs(synaptic_tau - membrane_tau)
        slow_decay = max(membrane_decay, synaptic_decay)
        exponent = (dt / membrane_tau) * (difference / synaptic_tau)
        coupling = slow_decay * (synaptic_tau / difference) * (-math.expm1(-exponent))
    if not all(math.isfinite(x) for x in (membrane_decay, synaptic_decay, coupling)):
        raise ValueError("time constants produce non-finite integration coefficients")
    return membrane_decay, synaptic_decay, coupling


def simulate_network(
    network: Network,
    *,
    duration_ms: float = 200.0,
    dt_ms: float = 0.1,
    external_current_nA=0.0,
    initial_mV=None,
    plasticity: STDPParameters | None = None,
    plastic_synapses=None,
    learning_enabled: bool = True,
) -> NetworkResult:
    """Simulate fixed or explicitly plastic connections with linear evolution.

    Input: scalar for all cells, (N,) constant per cell, or (steps,N) intervals.
    Spike times/reset are grid-quantized; delay must be at least one aligned step.
    Synaptic traces are interval START states AFTER arrivals; voltages include t=0.
    """
    if not isinstance(network, Network):
        raise ValueError("network must be a Network configuration")
    if type(learning_enabled) is not bool:
        raise ValueError("learning_enabled must be a boolean")
    if plasticity is not None and not isinstance(plasticity, STDPParameters):
        raise ValueError("plasticity must be STDPParameters or None")
    if plasticity is None and plastic_synapses is not None:
        raise ValueError("plastic_synapses requires a plasticity configuration")
    steps = step_count(duration_ms, dt_ms)
    n, p = network.n_neurons, network.neuron
    if (steps + 1) * n > MAX_TRACE_VALUES:
        raise ValueError(f"recording exceeds the {MAX_TRACE_VALUES:,}-value-per-array limit")
    outgoing = [[] for _ in range(n)]
    weights = np.array([s.weight_nA for s in network.synapses], dtype=np.float64)
    initial_weights = weights.copy()
    selected = ()
    rule = None
    weight_history = None
    local_index = np.full(len(weights), -1, dtype=np.int64)
    if plasticity is not None:
        selected = tuple(i for i, s in enumerate(network.synapses) if s.weight_nA > 0) if plastic_synapses is None else tuple(plastic_synapses)
        if (not selected or any(type(i) is not int or not 0 <= i < len(weights) for i in selected)
                or len(set(selected)) != len(selected)):
            raise ValueError("plastic synapse indices must be nonempty, unique and inside the network")
        if any(network.synapses[i].weight_nA <= 0 for i in selected):
            raise ValueError("only excitatory synapses support this plasticity rule")
        if (steps + 1) * len(selected) > MAX_TRACE_VALUES:
            raise ValueError("plastic weight history exceeds the recording memory limit")
        rule = PairSTDP(weights[list(selected)], plasticity)
        local_index[list(selected)] = np.arange(len(selected))
        weight_history = np.empty((steps + 1, len(selected)))
    plastic_targets = np.array([network.synapses[i].target for i in selected], dtype=np.int64)
    max_delay = 1
    for edge_index, edge in enumerate(network.synapses):
        ratio = edge.delay_ms / dt_ms
        if not math.isfinite(ratio):
            raise ValueError("delay / dt must be finite")
        delay = round(ratio)
        if delay < 1 or not math.isclose(ratio, delay, rel_tol=0, abs_tol=1e-7):
            raise ValueError("synaptic delays must be >= dt and integer multiples of dt")
        # Arrivals on or after the final endpoint cannot affect a recorded interval.
        if delay < steps or (rule is not None and delay <= steps):
            outgoing[edge.source].append((edge.target, edge.weight_nA, delay, edge_index))
            max_delay = max(max_delay, delay)
    queue_size = max_delay + 2
    if queue_size * n > MAX_TRACE_VALUES:
        raise ValueError("delay queue exceeds the recording memory limit")
    raw = np.asarray(external_current_nA, dtype=np.float64)
    if raw.ndim == 0:
        current = np.full((steps, n), float(raw))
    elif raw.shape == (n,):
        current = np.broadcast_to(raw, (steps, n)).copy()
    elif raw.shape == (steps, n):
        current = raw.copy()
    else:
        raise ValueError(f"external_current_nA must be scalar, ({n},) or ({steps}, {n})")
    if not np.isfinite(current).all():
        raise ValueError("external currents must be finite")
    initial = np.asarray(p.rest_mV if initial_mV is None else initial_mV, dtype=np.float64)
    if initial.ndim == 0:
        initial = np.full(n, float(initial))
    if initial.shape != (n,) or not np.isfinite(initial).all() or np.any(initial >= p.threshold_mV):
        raise ValueError("initial_mV must be scalar or (N,), finite and below threshold")
    with np.errstate(over="ignore", invalid="ignore"):
        external_equilibrium = p.rest_mV + p.resistance_MOhm * current
    if not np.isfinite(external_equilibrium).all():
        raise ValueError("external current and resistance produce non-finite voltages")
    ref_ratio = p.refractory_ms / dt_ms
    if not math.isfinite(ref_ratio):
        raise ValueError("refractory duration / dt must be finite")
    nearest = round(ref_ratio)
    ref_steps = nearest if math.isclose(ref_ratio, nearest, rel_tol=0, abs_tol=1e-9) else math.ceil(ref_ratio)
    # Remaining counters fit int64, even for refractoriness beyond the entire run.
    remaining = np.zeros(n, dtype=np.int64)
    ref_steps_for_run = min(ref_steps, steps + 1)
    membrane_decay, synaptic_decay, coupling = _decay_coefficients(dt_ms, p.tau_ms, network.synaptic_tau_ms)
    fraction = -math.expm1(-dt_ms / p.tau_ms)
    time_ms = np.arange(steps + 1, dtype=np.float64) * dt_ms
    voltage = np.empty((steps + 1, n), dtype=np.float64)
    voltage[0] = initial
    synaptic_trace = np.empty((steps, n), dtype=np.float64)
    pending = np.zeros((queue_size, n), dtype=np.float64)
    pending_plastic = [[] for _ in range(queue_size)] if rule is not None else None
    pending_plastic_count = 0
    previous_fired = np.empty(0, dtype=np.int64)
    synaptic_state = np.zeros(n, dtype=np.float64)
    spike_indices, spike_neurons = [], []
    # Catch numerical overflow instead of exporting invalid experiment results.
    with np.errstate(over="raise", invalid="raise"):
        try:
            for i in range(steps + 1):
                if i == steps and rule is None:
                    break
                slot = i % queue_size
                if i < steps:
                    synaptic_state += pending[slot]
                    pending[slot].fill(0)
                if rule is not None:
                    arrivals = pending_plastic[slot]
                    pending_plastic[slot] = []
                    pending_plastic_count -= len(arrivals)
                    # Transmission uses the weight BEFORE this timestamp's updates.
                    if i < steps and arrivals:
                        np.add.at(synaptic_state, plastic_targets[arrivals], rule.weights_nA[arrivals])
                    posts = np.flatnonzero(np.isin(plastic_targets, previous_fired))
                    if arrivals or len(posts):
                        rule.events(time_ms[i], pre_arrivals=arrivals, post_spikes=posts,
                                    learning_enabled=learning_enabled)
                    weights[list(selected)] = rule.weights_nA
                    weight_history[i] = rule.weights_nA
                if i == steps:
                    break
                synaptic_trace[i] = synaptic_state
                clamped = remaining > 0
                remaining[clamped] -= 1
                candidate = (membrane_decay * voltage[i] + fraction * external_equilibrium[i]
                             + (p.resistance_MOhm * coupling) * synaptic_state)
                candidate[clamped] = p.reset_mV
                fired = np.flatnonzero((~clamped) & (candidate >= p.threshold_mV))
                candidate[fired] = p.reset_mV
                voltage[i + 1] = candidate
                remaining[fired] = ref_steps_for_run
                previous_fired = fired
                for neuron in fired:
                    spike_indices.append(i + 1)
                    spike_neurons.append(int(neuron))
                    if len(spike_indices) > MAX_SPIKES:
                        raise ValueError(f"simulation exceeds the {MAX_SPIKES:,}-spike limit")
                    for target, weight, delay, edge_index in outgoing[neuron]:
                        arrival_index = i + 1 + delay
                        plastic_index = local_index[edge_index]
                        if rule is not None and plastic_index >= 0 and arrival_index <= steps:
                            pending_plastic_count += 1
                            if pending_plastic_count > MAX_PENDING_PLASTIC_EVENTS:
                                raise ValueError("pending plastic arrivals exceed the event queue limit")
                            pending_plastic[arrival_index % queue_size].append(int(plastic_index))
                        elif arrival_index < steps and plastic_index < 0:
                            pending[arrival_index % queue_size, target] += weight
                synaptic_state *= synaptic_decay
        except FloatingPointError as exc:
            raise ValueError("network state overflowed; reduce currents or connection strengths") from exc
    spike_times = time_ms[np.asarray(spike_indices, dtype=np.int64)].copy()
    spike_neurons = np.asarray(spike_neurons, dtype=np.int64)
    if not np.isfinite(voltage).all() or not np.isfinite(synaptic_trace).all():
        raise ValueError("network produced non-finite states")
    for array in (time_ms, voltage, current, synaptic_trace, spike_times, spike_neurons, initial_weights, weights):
        array.flags.writeable = False
    if weight_history is not None:
        weight_history.flags.writeable = False
    return NetworkResult(time_ms, voltage, current, synaptic_trace, spike_times, spike_neurons,
                         dt_ms, ref_steps * dt_ms, initial_weights, weights, weight_history, selected)
