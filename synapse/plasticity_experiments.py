"""Stimulus-driven calibration and circuit protocols for plasticity validation."""

from dataclasses import replace
import math
import numpy as np

from .lif import LIFParameters, step_count
from .network import Network, Synapse, simulate_network
from .plasticity import STDPParameters
from .stimuli import pulse_current

PAIR_LAGS_MS = (-40.0, -20.0, -10.0, -5.0, 0.0, 5.0, 10.0, 20.0, 40.0)


def _spike_pulse_amplitude(dt_ms, neuron):
    # Calibration stimulus: target twice the rest-to-threshold voltage increment.
    fraction = -math.expm1(-dt_ms / neuron.tau_ms)
    return 2 * (neuron.threshold_mV - neuron.rest_mV) / (neuron.resistance_MOhm * fraction)


def pair_protocol(lag_ms, dt_ms=0.1, delay_ms=1.0):
    """One source spike and one target spike produced by one-interval currents.

    Desired lag = target spike time - source spike ARRIVAL time.
    Actual spike times must be measured; they are never assigned to the result.
    """
    duration = 130.0
    steps = step_count(duration, dt_ms)
    if not math.isfinite(lag_ms) or not -40 <= lag_ms <= 40:
        raise ValueError("pair lag must lie in [-40, 40] ms")
    neuron = LIFParameters()
    network = Network(2, (Synapse(0, 1, 0.1, delay_ms),), neuron=neuron)
    amplitude = _spike_pulse_amplitude(dt_ms, neuron)
    pre_start = 60.0
    post_start = pre_start + delay_ms + lag_ms
    drive = np.zeros((steps, 2))
    recipe = []
    for cell, start in ((0, pre_start), (1, post_start)):
        pulses = [(start, start + dt_ms, amplitude)]
        drive[:, cell] = pulse_current(duration_ms=duration, dt_ms=dt_ms, pulses=pulses)
        recipe.append({"neuron": cell, "pulses": pulses})
    return network, drive, duration, recipe


def run_pair(lag_ms, *, dt_ms=0.1, delay_ms=1.0, parameters=None, learning_enabled=True):
    p = parameters if parameters is not None else STDPParameters()
    network, drive, duration, recipe = pair_protocol(lag_ms, dt_ms, delay_ms)
    result = simulate_network(network, duration_ms=duration, dt_ms=dt_ms,
                              external_current_nA=drive, plasticity=p, learning_enabled=learning_enabled)
    if not np.array_equal(result.spike_counts, [1, 1]):
        raise ValueError("pair calibration did not produce exactly one computed spike per cell")
    pre = float(result.spike_times_ms[result.spike_neurons == 0][0])
    post = float(result.spike_times_ms[result.spike_neurons == 1][0])
    lag = post - (pre + delay_ms)
    # Event coincidence is defined by integer ticks, not float subtraction noise.
    ticks = round(post / dt_ms) - round(pre / dt_ms) - round(delay_ms / dt_ms)
    lag = ticks * dt_ms
    if not learning_enabled or ticks == 0:
        expected = 0.0
    elif ticks > 0:
        expected = p.a_plus_nA * math.exp(-lag / p.tau_plus_ms)
    else:
        expected = -p.a_minus_nA * math.exp(lag / p.tau_minus_ms)
    expected_final = float(np.clip(network.synapses[0].weight_nA + expected, p.w_min_nA, p.w_max_nA))
    record = {"requested_lag_ms": lag_ms, "measured_lag_ms": lag,
              "computed_source_spike_ms": pre, "computed_arrival_ms": pre + delay_ms,
              "computed_target_spike_ms": post, "initial_weight_nA": float(result.initial_weights_nA[0]),
              "final_weight_nA": float(result.final_weights_nA[0]),
              "measured_change_nA": float(result.final_weights_nA[0] - result.initial_weights_nA[0]),
              "analytic_final_weight_nA": expected_final,
              "error_nA": float(result.final_weights_nA[0] - expected_final),
              "learning_enabled": learning_enabled, "delay_ms": delay_ms, "dt_ms": dt_ms,
              "duration_ms": duration, "stimulus_recipe": recipe}
    return record, result, network


def circuit_protocol(dt_ms=0.1, repeats=12):
    if type(repeats) is not int or not 1 <= repeats <= 20:
        raise ValueError("repeats must be an integer from 1 to 20")
    duration = repeats * 100.0 + 50.0
    steps = step_count(duration, dt_ms)
    edges = tuple(Synapse(i, 8 + i // 2, 0.1, 1.0) for i in range(6)) + (Synapse(11, 10, -0.05, 1.0),)
    network = Network(12, edges, inhibitory_neurons=(11,))
    amplitude = _spike_pulse_amplitude(dt_ms, network.neuron)
    starts = [20.0 + i * 100.0 for i in range(repeats)]
    recipes = []
    drive = np.zeros((steps, 12))
    # N8 is driven after arrival, N9 before arrival, N10 receives no forced spikes.
    for cell in (*range(6), 8, 9, 11):
        offset = 11.0 if cell == 8 else -9.0 if cell == 9 else 0.0
        pulses = [(s + offset, s + offset + dt_ms, amplitude) for s in starts]
        drive[:, cell] = pulse_current(duration_ms=duration, dt_ms=dt_ms, pulses=pulses)
        recipes.append({"neuron": cell, "pulses": pulses})
    return network, drive, duration, recipes


def frozen_network(network, weights_nA):
    """Copy a fitted circuit for a fresh, learning-free response probe.

    A zero-strength connection is omitted; no membrane state or traces transfer.
    """
    weights = np.asarray(weights_nA, dtype=float)
    if weights.shape != (len(network.synapses),) or not np.isfinite(weights).all():
        raise ValueError("one finite weight per connection is required")
    edges = tuple(replace(edge, weight_nA=float(w)) for edge, w in zip(network.synapses, weights) if w != 0)
    return replace(network, synapses=edges)


def probe_protocol(network, dt_ms=0.1):
    """Fresh source-only pulse, with no teaching input to N8, N9 or N10."""
    duration = 100.0
    steps = step_count(duration, dt_ms)
    amplitude = _spike_pulse_amplitude(dt_ms, network.neuron)
    drive = np.zeros((steps, network.n_neurons))
    recipes = []
    for cell in (*range(6), 11):
        pulses = [(20.0, 20.0 + dt_ms, amplitude)]
        drive[:, cell] = pulse_current(duration_ms=duration, dt_ms=dt_ms, pulses=pulses)
        recipes.append({"neuron": cell, "pulses": pulses})
    return drive, duration, recipes
