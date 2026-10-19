"""Offline illustration and measured replay assets for the first guided lesson."""

import json
from pathlib import Path

import numpy as np

from .guided_timing import CONDITIONS, DELAY_MS, DT_MS, PERIOD_MS, RULE

ASSETS = Path(__file__).resolve().parents[1] / 'ui_assets'


def biology_html():
    from .region_view import asset_uri
    return ((ASSETS / 'guided_biology.html').read_text(encoding='utf-8')
            .replace('__GUIDED_CSS__', (ASSETS / 'guided.css').read_text(encoding='utf-8'))
            .replace('__MEDICAL_SYNAPSE__', asset_uri('synapse_detail.png'))
            .replace('__BIOLOGY_JS__', (ASSETS / 'guided_biology.js').read_text(encoding='utf-8')))


def replay_payload(experiment, condition='chosen', pair=1):
    if condition not in CONDITIONS:
        raise ValueError('Unknown timing condition.')
    if type(pair) is not int or not 1 <= pair <= experiment.config.repeats:
        raise ValueError('Choose a recorded pair from this experiment.')
    run = experiment.runs[condition]
    r = run.result
    offset = (pair - 1) * PERIOD_MS
    times = r.spike_times_ms
    mask = (times >= offset) & (times < offset + PERIOD_MS)
    spikes = np.column_stack((times[mask], r.spike_neurons[mask])).tolist()
    pre = next(t for t, cell in spikes if cell == 0)
    post = next(t for t, cell in spikes if cell == 1)
    arrival = pre + DELAY_MS
    start = max(offset, min(pre, post) - 8.0)
    stop = min(offset + PERIOD_MS, max(arrival, post) + 30.0)
    lo, hi = round(start / DT_MS), round(stop / DT_MS)
    pulses = [{'cell': item['neuron'], 'start': p[0], 'end': p[1]}
              for item in run.stimulus_recipe for p in item['pulses']
              if offset <= p[0] < offset + PERIOD_MS]
    # At arrival the engine transmits with the weight before that timestamp's update.
    transmission = float(r.weight_history_nA[round(arrival / DT_MS) - 1, 0])
    updates = []
    for i in range(max(1, lo), hi + 1):
        old, new = r.weight_history_nA[i - 1, 0], r.weight_history_nA[i, 0]
        if old != new:
            updates.append({'time': float(r.time_ms[i]), 'before': float(old), 'after': float(new)})
    return {
        'format': 'synapse-guided-replay-v1', 'condition': condition,
        'label': CONDITIONS[condition], 'pair': pair, 'pairs': experiment.config.repeats,
        'learning': run.learning_enabled, 'start': start, 'stop': stop, 'dt': DT_MS,
        'lag': run.measured_lags_ms[pair - 1], 'delay': DELAY_MS,
        'spikes': spikes, 'arrival': arrival, 'sourceSpike': pre, 'targetSpike': post,
        'transmittedWeight': transmission, 'pulses': pulses, 'updates': updates,
        'rest': -65.0, 'threshold': -50.0,
        'time': r.time_ms[lo:hi + 1].tolist(),
        'voltage': r.voltage_mV[lo:hi + 1].tolist(),
        'weights': r.weight_history_nA[lo:hi + 1, 0].tolist(),
        'bounds': [RULE.w_min_nA, RULE.w_max_nA],
    }


def replay_html(data):
    raw = json.dumps(data, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    return ((ASSETS / 'guided_replay.html').read_text(encoding='utf-8')
            .replace('__GUIDED_CSS__', (ASSETS / 'guided.css').read_text(encoding='utf-8'))
            .replace('__GUIDED_CORE__', (ASSETS / 'guided_core.js').read_text(encoding='utf-8'))
            .replace('__GUIDED_REPLAY_JS__', (ASSETS / 'guided_replay.js').read_text(encoding='utf-8'))
            .replace('__GUIDED_DATA__', raw))
