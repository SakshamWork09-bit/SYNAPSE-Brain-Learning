"""Controlled two-cell timing lesson. All recordings use the reference engine.

External pulses evoke both spikes during training. A separate, fresh-state,
source-only probe measures transmission with learning disabled. No live
workspace or random generator is accessed by this module.
"""

from dataclasses import asdict, dataclass
import json
import math

import numpy as np

from .lif import step_count
from .network import Network, NetworkResult, Synapse, simulate_network
from .plasticity import STDPParameters
from .plasticity_experiments import _spike_pulse_amplitude
from .stimuli import pulse_current

DT_MS = 0.5
DELAY_MS = 1.0
PERIOD_MS = 400.0
PRE_START_MS = 180.0
INITIAL_WEIGHT_NA = 0.1
RULE = STDPParameters(w_max_nA=0.35)
CONDITIONS = {
    'chosen': 'Your timing',
    'opposite': 'Opposite timing',
    'disabled': 'Learning disabled',
    'distant': 'Far-apart timing',
}


@dataclass(frozen=True)
class TimingConfig:
    lag_ms: int = 10
    repeats: int = 1

    def __post_init__(self):
        if type(self.lag_ms) is not int or not -40 <= self.lag_ms <= 40:
            raise ValueError('Timing must be an integer from -40 to 40 ms.')
        if type(self.repeats) is not int or not 1 <= self.repeats <= 20:
            raise ValueError('Use 1 to 20 spike pairs.')


def _network(weight=INITIAL_WEIGHT_NA):
    return Network(2, (Synapse(0, 1, weight, DELAY_MS),))


def _protocol(lag, repeats):
    network = _network()
    duration = PERIOD_MS * repeats
    drive = np.zeros((step_count(duration, DT_MS), 2))
    amplitude = _spike_pulse_amplitude(DT_MS, network.neuron)
    recipe = []
    for cell, offset in ((0, 0), (1, DELAY_MS + lag)):
        starts = [PRE_START_MS + PERIOD_MS * k + offset for k in range(repeats)]
        pulses = [(s, s + DT_MS, amplitude) for s in starts]
        drive[:, cell] = pulse_current(duration_ms=duration, dt_ms=DT_MS, pulses=pulses)
        recipe.append({'neuron': cell, 'pulses': pulses})
    return network, drive, duration, recipe


def _probe(weight):
    """Source is driven once; target receives only the computed synaptic input."""
    network = _network(weight)
    duration = 80.0
    drive = np.zeros((step_count(duration, DT_MS), 2))
    drive[:, 0] = pulse_current(duration_ms=duration, dt_ms=DT_MS,
        pulses=[(20.0, 20.0 + DT_MS, _spike_pulse_amplitude(DT_MS, network.neuron))])
    return simulate_network(network, duration_ms=duration, dt_ms=DT_MS,
                            external_current_nA=drive, learning_enabled=False)


def _peak(result):
    return float(np.max(result.voltage_mV[:, 1]) - _network().neuron.rest_mV)


@dataclass(frozen=True)
class TimingRun:
    condition: str
    requested_lag_ms: int
    learning_enabled: bool
    result: NetworkResult
    stimulus_recipe: list
    probe: NetworkResult

    @property
    def measured_lags_ms(self):
        r = self.result
        pre = r.spike_times_ms[r.spike_neurons == 0]
        post = r.spike_times_ms[r.spike_neurons == 1]
        return (post - pre - DELAY_MS).tolist()

    @property
    def final_weight(self):
        return float(self.result.final_weights_nA[0])

    def summary(self):
        r = self.result
        return {
            'condition': self.condition, 'label': CONDITIONS[self.condition],
            'requested_lag_ms': self.requested_lag_ms,
            'measured_lags_ms': self.measured_lags_ms,
            'learning_enabled': self.learning_enabled,
            'initial_weight_nA': INITIAL_WEIGHT_NA, 'final_weight_nA': self.final_weight,
            'change_nA': self.final_weight - INITIAL_WEIGHT_NA,
            'spike_counts': r.spike_counts.tolist(),
            'probe_peak_above_rest_mV': _peak(self.probe),
            'at_bound': math.isclose(self.final_weight, RULE.w_min_nA, abs_tol=1e-12)
                        or math.isclose(self.final_weight, RULE.w_max_nA, abs_tol=1e-12),
        }


@dataclass(frozen=True)
class TimingExperiment:
    config: TimingConfig
    runs: dict[str, TimingRun]
    initial_probe: NetworkResult

    def export(self):
        from . import __version__
        conditions = {}
        for key, run in self.runs.items():
            r = run.result
            changed = np.flatnonzero(np.diff(r.weight_history_nA[:, 0]) != 0) + 1
            conditions[key] = {
                **run.summary(), 'stimulus_recipe': run.stimulus_recipe,
                'spikes_ms_and_cell': np.column_stack((r.spike_times_ms, r.spike_neurons)).tolist(),
                'weight_updates_ms_and_nA': [[float(r.time_ms[i]), float(r.weight_history_nA[i, 0])]
                                             for i in changed],
                'probe_target_voltage_mV': run.probe.voltage_mV[:, 1].tolist(),
            }
        return {
            'format': 'synapse-guided-timing-v1', 'synapse_version': __version__,
            'numpy_version': np.__version__, 'config': asdict(self.config),
            'dt_ms': DT_MS, 'delay_ms': DELAY_MS, 'period_ms': PERIOD_MS,
            'duration_ms': self.config.repeats * PERIOD_MS,
            'network': {'neurons': 2, 'connections': 1, 'initial_weight_nA': INITIAL_WEIGHT_NA,
                        'neuron': asdict(_network().neuron), 'synaptic_tau_ms': 5.0},
            'rule': asdict(RULE), 'conditions': conditions,
            'initial_probe': {'peak_above_rest_mV': _peak(self.initial_probe),
                              'time_ms': self.initial_probe.time_ms.tolist(),
                              'target_voltage_mV': self.initial_probe.voltage_mV[:, 1].tolist(),
                              'source_pulse_start_ms': 20.0, 'learning_enabled': False},
            'notes': ['Both training spikes are externally evoked.',
                      'All conditions start from rest at the same initial weight.',
                      'Repetitions are 400 ms apart; all-to-all traces continue within a run.',
                      'Far-apart timing is +/-150 ms and need not produce exactly zero change.',
                      'A probe starts from rest, drives only A and freezes learning.',
                      'This is a specified model rule, not a measurement from a human brain.'],
        }

    def json_bytes(self):
        return json.dumps(self.export(), indent=2, allow_nan=False).encode('utf-8')


def run_experiment(config=None):
    config = config if config is not None else TimingConfig()
    if not isinstance(config, TimingConfig):
        raise ValueError('config must be TimingConfig.')
    runs = {}
    for condition, lag, enabled in (
        ('chosen', config.lag_ms, True),
        ('opposite', -config.lag_ms, True),
        ('disabled', config.lag_ms, False),
        ('distant', 150 if config.lag_ms >= 0 else -150, True),
    ):
        network, drive, duration, recipe = _protocol(lag, config.repeats)
        result = simulate_network(network, duration_ms=duration, dt_ms=DT_MS,
            external_current_nA=drive, plasticity=RULE, learning_enabled=enabled)
        if not np.array_equal(result.spike_counts, [config.repeats, config.repeats]):
            raise ValueError('The calibration must evoke exactly one spike per neuron per pair.')
        runs[condition] = TimingRun(condition, lag, enabled, result, recipe,
                                   _probe(float(result.final_weights_nA[0])))
    return TimingExperiment(config, runs, _probe(INITIAL_WEIGHT_NA))


def explanation(experiment):
    run = experiment.runs['chosen']
    change = run.final_weight - INITIAL_WEIGHT_NA
    if change > 1e-10:
        outcome = 'strengthened'
    elif change < -1e-10:
        outcome = 'weakened'
    else:
        outcome = 'stayed unchanged' if change == 0 else 'was unchanged at six-decimal precision'
    lag = run.measured_lags_ms[0]
    timing = (f"B fired {abs(lag):g} ms {'after' if lag > 0 else 'before'} A’s signal arrived."
              if lag != 0 else 'B fired at the same simulated time as A’s signal arrived.')
    text = (f'The connection {outcome}: {INITIAL_WEIGHT_NA:.6f} → {run.final_weight:.6f} nA. '
            f'{timing} The learning-disabled copy received the same input and kept its initial strength.')
    if run.summary()['at_bound']:
        text += ' The weight reached a configured bound; further repetition is limited by that bound.'
    if lag == 0:
        text += ' A new zero-lag pair contributes no change by our convention.'
        if experiment.config.repeats > 1:
            text += ' Older pairs leave a tiny residual because their traces continue between repetitions.'
    return text


def notebook(experiment, prediction='I am unsure'):
    rows = ['# SYNAPSE · Timing experiment', '',
            f'My prediction before running: {prediction}', '',
            f'Changed variable: B spike minus A signal arrival = {experiment.config.lag_ms} ms.',
            f'Budget: {experiment.config.repeats} pair(s) per condition; initial strength 0.100000 nA.', '',
            explanation(experiment), '',
            '| Condition | Measured lag (ms) | Final strength (nA) | Probe peak above rest (mV) |',
            '| --- | ---: | ---: | ---: |']
    for run in experiment.runs.values():
        s = run.summary()
        rows.append(f"| {s['label']} | {s['measured_lags_ms'][0]:g} | {s['final_weight_nA']:.6f} | {s['probe_peak_above_rest_mV']:.6f} |")
    rows.extend(['', 'Probe: A is stimulated, B is not directly stimulated, and learning is frozen.', '',
                 'Interpretation: a controlled demonstration of the specified pair-STDP rule.',
                 'Limit: this simplified circuit does not establish how a whole human brain learns.', '',
                 'Biological motivation: Bi & Poo (1998), cultured rat hippocampal neurons.',
                 'https://pubmed.ncbi.nlm.nih.gov/9852584/', ''])
    return '\n'.join(rows)
