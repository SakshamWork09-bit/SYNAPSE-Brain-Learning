"""Independent model experiments embedded in the neuroscience course."""

from dataclasses import dataclass, asdict
import json

import numpy as np

from .integrated import IntegratedSession
from .interventions import ProbeConfig, edge_presets, run_probe
from .lif import simulate, LIFParameters
from .network import Network, Synapse, simulate_network
from .plasticity_experiments import _spike_pulse_amplitude
from .stimuli import pulse_current
from .replay import replay_payload, probe_payload


@dataclass(frozen=True)
class BranchConfig:
    amplitude_nA: float = .8
    pathway_gain: float = 1.0
    inhibition_gain: float = 1.0
    cue: int = 0

    def __post_init__(self):
        for v, lo, hi in [(self.amplitude_nA, 0, 1), (self.pathway_gain, 0, 2), (self.inhibition_gain, 0, 2)]:
            if type(v) not in (int, float) or not np.isfinite(v) or not lo <= v <= hi:
                raise ValueError('Course pulse/gains are outside their bounds.')
        if type(self.cue) is not int or self.cue not in (0, 1):
            raise ValueError('Choose cue 0 or 1.')


def branch_experiment(config=None):
    config = config or BranchConfig()
    if not isinstance(config, BranchConfig): raise ValueError('Expected BranchConfig.')
    source = IntegratedSession(7)
    label = 'Sensory A → association A' if config.cue == 0 else 'Sensory B → association B'
    edges = edge_presets(source.engine.network)[label]
    return run_probe(source.engine, ProbeConfig(neurons=tuple(range(5*config.cue, 5*config.cue+5)),
        amplitude_nA=float(config.amplitude_nA), edges=edges, edge_gain=float(config.pathway_gain),
        inhibitory_gain=float(config.inhibition_gain), initial_state='resting'))


def branch_payload(result=None, branch='intervention'):
    if result is None:
        data = replay_payload(IntegratedSession(7))
    else:
        data = probe_payload(result, branch, seed=7)
    data['course'] = {'title':'Launch a signal. Follow its branches.',
                      'intro':'A calculated model recording. The columns show engineered roles, not locations in the human brain.'}
    return data


def neuron_experiment(current_nA=.25):
    if type(current_nA) not in (int, float) or not np.isfinite(current_nA) or not 0 <= current_nA <= .6:
        raise ValueError('Choose input from 0 to 0.6 nA.')
    current = pulse_current(duration_ms=200, dt_ms=.2, pulses=[(20, 180, float(current_nA))])
    return simulate(duration_ms=200, dt_ms=.2, current_nA=current)


def synapse_experiment(weight_nA=.1):
    if type(weight_nA) not in (int, float) or not np.isfinite(weight_nA) or not -.3 <= weight_nA <= .3:
        raise ValueError('Choose strength from -0.3 to +0.3 nA.')
    edges = (Synapse(0, 1, float(weight_nA), 1.0),) if weight_nA != 0 else ()
    network = Network(2, edges, inhibitory_neurons=(0,) if weight_nA < 0 else ())
    drive = np.zeros((400, 2))
    drive[:, 0] = pulse_current(duration_ms=80, dt_ms=.2,
        pulses=[(20, 20.2, _spike_pulse_amplitude(.2, LIFParameters()))])
    return simulate_network(network, duration_ms=80, dt_ms=.2, external_current_nA=drive)


def notebook_bytes(progress, notes):
    payload = {'format':'synapse-course-notebook-v1','explored':list(progress),'notes':dict(notes)}
    data = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
    load_notebook(data)
    return data


def load_notebook(data):
    from .course_content import CHAPTER_BY_ID
    from .region_content import LESSON_BY_ID
    known = set(CHAPTER_BY_ID) | set(LESSON_BY_ID)
    if not isinstance(data, bytes) or len(data) > 256*1024:
        raise ValueError('Notebook must be JSON of at most 256 KiB.')
    try:
        p = json.loads(data)
        if not isinstance(p, dict) or p.get('format') != 'synapse-course-notebook-v1': raise ValueError('Wrong notebook format.')
        explored, notes = p['explored'], p['notes']
        if not isinstance(explored, list) or len(explored) > len(known) or len(set(explored)) != len(explored): raise ValueError('Invalid explored chapters.')
        if any(type(k) is not str or k not in known for k in explored): raise ValueError('Unknown chapter.')
        if not isinstance(notes, dict) or len(notes) > len(known): raise ValueError('Invalid notes.')
        if any(k not in known or type(v) is not str or len(v) > 10000 for k, v in notes.items()): raise ValueError('Invalid note text.')
        return explored.copy(), notes.copy()
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f'Notebook was not loaded: {exc}') from exc


def notebook_markdown(progress, notes):
    from .course_content import CHAPTERS
    from .region_content import LESSONS
    lines = ['# My SYNAPSE learning notebook', '', 'Explored marks are self-reported, not assessed mastery.', '']
    for c in (*LESSONS,*CHAPTERS):
        lines += [f"## {c['number']} · {c['title']}", '',
                  'Explored: '+('yes' if c['id'] in progress else 'not marked'), '',
                  notes.get(c['id'], '') or 'No reflection saved yet.', '']
    return '\n'.join(lines)
