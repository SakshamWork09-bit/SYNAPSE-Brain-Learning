"""Deterministic input currents; pulse boundaries must align to the time grid."""

import math
import numpy as np

from .lif import step_count


def pulse_current(*, duration_ms, dt_ms, pulses, baseline_nA=0.0):
    """Sum (start_ms, stop_ms, amplitude_nA) pulses on [start, stop)."""
    steps = step_count(duration_ms, dt_ms)
    if not math.isfinite(baseline_nA):
        raise ValueError("baseline_nA must be finite")
    current = np.full(steps, baseline_nA, dtype=np.float64)
    for start, stop, amplitude in pulses:
        if not all(math.isfinite(x) for x in (start, stop, amplitude)):
            raise ValueError("pulse values must be finite")
        if not 0 <= start < stop <= duration_ms:
            raise ValueError("pulse must satisfy 0 <= start < stop <= duration_ms")
        indices = []
        for boundary in (start, stop):
            index = round(boundary / dt_ms)
            if not math.isclose(boundary / dt_ms, index, rel_tol=0, abs_tol=1e-7):
                raise ValueError("pulse boundaries must align to dt_ms")
            indices.append(index)
        current[indices[0]:indices[1]] += amplitude
    if not np.isfinite(current).all():
        raise ValueError("overlapping pulses produced non-finite current")
    return current
