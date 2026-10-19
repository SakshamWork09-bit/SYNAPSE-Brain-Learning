"""Current-driven leaky integrate-and-fire neuron. Units: ms, mV, nA, MOhm.

Exact subthreshold updates for piecewise-constant current; threshold detection
and reset occur at grid endpoints. See docs/MODEL.md for timing conventions.
"""

from dataclasses import asdict, dataclass
import math

import numpy as np

MAX_STEPS = 1_000_000


@dataclass(frozen=True)
class LIFParameters:
    rest_mV: float = -65.0
    reset_mV: float = -65.0
    threshold_mV: float = -50.0
    tau_ms: float = 20.0
    resistance_MOhm: float = 100.0
    refractory_ms: float = 2.0

    def __post_init__(self):
        for name, value in asdict(self).items():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if self.tau_ms <= 0 or self.resistance_MOhm <= 0:
            raise ValueError("tau_ms and resistance_MOhm must be positive")
        if self.refractory_ms < 0:
            raise ValueError("refractory_ms must be nonnegative")
        if max(self.rest_mV, self.reset_mV) >= self.threshold_mV:
            raise ValueError("rest and reset voltages must be below threshold")


def step_count(duration_ms: float, dt_ms: float) -> int:
    """Validate the time grid before allocating simulation arrays."""
    if not math.isfinite(duration_ms) or not math.isfinite(dt_ms):
        raise ValueError("duration_ms and dt_ms must be finite")
    if duration_ms <= 0 or dt_ms <= 0:
        raise ValueError("duration_ms and dt_ms must be positive")
    ratio = duration_ms / dt_ms
    if not math.isfinite(ratio) or ratio > MAX_STEPS:
        raise ValueError(f"simulation exceeds the {MAX_STEPS:,}-step limit")
    steps = round(ratio)
    if steps < 1 or not math.isclose(ratio, steps, rel_tol=0, abs_tol=1e-7):
        raise ValueError("duration_ms must be an integer multiple of dt_ms")
    return steps


@dataclass(frozen=True)
class SimulationResult:
    time_ms: np.ndarray
    voltage_mV: np.ndarray
    current_nA: np.ndarray
    spike_times_ms: np.ndarray
    dt_ms: float
    effective_refractory_ms: float

    @property
    def rate_hz(self) -> float:
        """Finite-window spike count divided by duration, not steady-state rate."""
        return len(self.spike_times_ms) * 1000.0 / self.time_ms[-1]


def simulate(
    parameters: LIFParameters | None = None,
    *,
    duration_ms: float = 200.0,
    dt_ms: float = 0.1,
    current_nA: float | np.ndarray = 0.0,
    initial_mV: float | None = None,
) -> SimulationResult:
    """Return voltage states and spike events for a single deterministic neuron.

    current_nA is a scalar or one value per interval [t_i, t_(i+1)).
    voltage_mV includes t=0 and stores the post-reset state at spike endpoints.
    Refractory duration is rounded UP to whole intervals (with roundoff tolerance).
    """
    p = parameters if parameters is not None else LIFParameters()
    steps = step_count(duration_ms, dt_ms)
    initial = p.rest_mV if initial_mV is None else initial_mV
    if not math.isfinite(initial) or initial >= p.threshold_mV:
        raise ValueError("initial_mV must be finite and below threshold")
    raw = np.asarray(current_nA, dtype=np.float64)
    if raw.ndim == 0:
        current = np.full(steps, float(raw), dtype=np.float64)
    elif raw.shape == (steps,):
        current = raw.copy()
    else:
        raise ValueError(f"current_nA must be scalar or have shape ({steps},)")
    if not np.isfinite(current).all():
        raise ValueError("current_nA must contain only finite values")
    # Check derived values too: finite inputs can still overflow when multiplied.
    with np.errstate(over="ignore", invalid="ignore"):
        equilibrium = p.rest_mV + p.resistance_MOhm * current
    if not np.isfinite(equilibrium).all():
        raise ValueError("current and resistance produce non-finite voltages")
    time = np.arange(steps + 1, dtype=np.float64) * dt_ms
    voltage = np.empty(steps + 1, dtype=np.float64)
    voltage[0] = initial
    # -expm1 is accurate even for dt much smaller than tau.
    fraction = -math.expm1(-dt_ms / p.tau_ms)
    ref_ratio = p.refractory_ms / dt_ms
    if not math.isfinite(ref_ratio):
        raise ValueError("refractory_ms / dt_ms must be finite")
    nearest = round(ref_ratio)
    ref_steps = nearest if math.isclose(ref_ratio, nearest, abs_tol=1e-9, rel_tol=0) else math.ceil(ref_ratio)
    remaining = 0
    spike_indices = []
    for i in range(steps):
        if remaining:
            voltage[i + 1] = p.reset_mV
            remaining -= 1
            continue
        # Convex combination avoids overflow in equilibrium - voltage.
        candidate = (1.0 - fraction) * voltage[i] + fraction * equilibrium[i]
        if candidate >= p.threshold_mV:
            spike_indices.append(i + 1)
            voltage[i + 1] = p.reset_mV
            remaining = ref_steps
        else:
            voltage[i + 1] = candidate
    spikes = time[np.asarray(spike_indices, dtype=np.int64)].copy()
    for array in (time, voltage, current, spikes):
        array.flags.writeable = False
    return SimulationResult(time, voltage, current, spikes, dt_ms, ref_steps * dt_ms)
