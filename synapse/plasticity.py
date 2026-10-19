"""Bounded additive, all-to-all pair STDP, timed at local synaptic arrivals.

Equal-time pre/post events are handled together; their zero-lag pair contributes
nothing. Older pairs still contribute. This convention is explicit, not universal.
"""

from dataclasses import asdict, dataclass
import math
import numpy as np


@dataclass(frozen=True)
class STDPParameters:
    a_plus_nA: float = 0.02
    a_minus_nA: float = 0.021
    tau_plus_ms: float = 20.0
    tau_minus_ms: float = 20.0
    w_min_nA: float = 0.001
    w_max_nA: float = 2.0

    def __post_init__(self):
        if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in asdict(self).values()):
            raise ValueError("STDP parameters must be finite numbers")
        if min(self.a_plus_nA, self.a_minus_nA) < 0:
            raise ValueError("STDP step amplitudes must be nonnegative")
        if min(self.tau_plus_ms, self.tau_minus_ms) <= 0:
            raise ValueError("STDP time constants must be positive")
        if not 0 <= self.w_min_nA < self.w_max_nA:
            raise ValueError("STDP bounds must satisfy 0 <= minimum < maximum")


class PairSTDP:
    """Event-driven state for a vector of selected excitatory synapses."""

    def __init__(self, initial_weights_nA, parameters=None):
        self.parameters = parameters if parameters is not None else STDPParameters()
        if not isinstance(self.parameters, STDPParameters):
            raise ValueError("parameters must be STDPParameters")
        self.weights_nA = np.asarray(initial_weights_nA, dtype=np.float64).copy()
        p = self.parameters
        if self.weights_nA.ndim != 1 or len(self.weights_nA) == 0:
            raise ValueError("initial weights must be a nonempty vector")
        if (not np.isfinite(self.weights_nA).all() or np.any(self.weights_nA < p.w_min_nA)
                or np.any(self.weights_nA > p.w_max_nA)):
            raise ValueError("initial plastic weights must lie within the configured bounds")
        self._pre = np.zeros_like(self.weights_nA)
        self._post = np.zeros_like(self.weights_nA)
        self._last_time = None

    def _indices(self, values):
        values = tuple(values)
        if any(not isinstance(x, (int, np.integer)) or isinstance(x, (bool, np.bool_)) for x in values):
            raise ValueError("event indices must be integers")
        indices = np.asarray(values, dtype=np.int64)
        if len(set(values)) != len(values) or np.any(indices < 0) or np.any(indices >= len(self.weights_nA)):
            raise ValueError("event indices must be unique and inside the plastic synapse vector")
        return indices

    def events(self, time_ms, *, pre_arrivals=(), post_spikes=(), learning_enabled=True):
        """Process one combined timestamp; every listed edge fires at most once.

        Indices refer to this local plastic-edge vector, not neuron indices.
        Pre arrivals and postsynaptic spikes at one timestamp MUST be batched.
        """
        if not math.isfinite(time_ms) or time_ms < 0:
            raise ValueError("event time must be finite and nonnegative")
        if self._last_time is not None and time_ms <= self._last_time:
            raise ValueError("event timestamps must increase; combine simultaneous events")
        if type(learning_enabled) is not bool:
            raise ValueError("learning_enabled must be a boolean")
        pre, post = self._indices(pre_arrivals), self._indices(post_spikes)
        p = self.parameters
        elapsed = 0.0 if self._last_time is None else time_ms - self._last_time
        self._pre *= math.exp(-elapsed / p.tau_plus_ms)
        self._post *= math.exp(-elapsed / p.tau_minus_ms)
        if learning_enabled:
            with np.errstate(over='raise', invalid='raise'):
                try:
                    delta = np.zeros_like(self.weights_nA)
                    delta[pre] -= p.a_minus_nA * self._post[pre]
                    delta[post] += p.a_plus_nA * self._pre[post]
                    updated = self.weights_nA + delta
                except FloatingPointError as exc:
                    raise ValueError("STDP update overflowed; reduce the learning amplitudes") from exc
            self.weights_nA[:] = np.clip(updated, p.w_min_nA, p.w_max_nA)
        # Increment AFTER evaluating both directions: no new zero-lag pairing.
        self._pre[pre] += 1.0
        self._post[post] += 1.0
        self._last_time = time_ms
