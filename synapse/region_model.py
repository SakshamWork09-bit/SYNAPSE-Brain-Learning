"""A 100-cell, inspectable teaching circuit shared by the region lessons.

The groups are engineering roles, NOT brain regions. The fixed encoder is spiking;
the bounded, positive readout uses supervised normalized delta updates between
presentations. Inference receives an input signal and weights, never its label.
"""

from dataclasses import dataclass, asdict
import copy
import hashlib
import json
import math

import numpy as np

from .continuing import ContinuingNetwork
from .network import Network, Synapse
from .laboratory import ActivityWindow
from .memory_lab import Signal, Task, examples

DT = .5
FEATURES = tuple(range(18)) + tuple(range(21, 81)) + tuple(range(95, 100))
OUTPUTS = (tuple(range(87, 91)), tuple(range(91, 95)))
LOW, HIGH = .001, .012
BASE = (LOW + HIGH) / 2
GROUPS = (
    ('visual', 'Visual input', tuple(range(18)), '#147d92', 'Nine OFF/ON pixel pairs. These are engineered input channels, not retinal cells.'),
    ('symbols', 'Symbol input', tuple(range(18, 21)), '#5968a5', 'A, B and C arrive as externally supplied current pulses.'),
    ('history', 'Delayed traces', tuple(range(21, 69)), '#8b61a5', 'Sixteen delay taps for each symbol preserve different recent histories.'),
    ('association', 'Convergence', tuple(range(69, 81)), '#b66a43', 'Inputs converge through fixed positive links; weak feedback also exists.'),
    ('inhibition', 'Inhibitory cells', tuple(range(81, 87)), '#bc586d', 'These six cells send negative current to convergence and context cells.'),
    ('readout', 'Class readout', tuple(range(87, 95)), '#218470', 'Four passive LIF voltages per class. Their mean difference determines the model answer.'),
    ('context', 'Context input', tuple(range(95, 99)), '#9a7934', 'A controllable external context pulse; no hormone or emotion is calculated.'),
    ('clock', 'Readout cue', (99,), '#6b7b86', 'A fixed protocol cue ten milliseconds before the voltage is read.'),
)


@dataclass(frozen=True)
class Protocol:
    extra_delay_ms: float = 0.
    relay_gain: float = 1.
    inhibition_gain: float = 1.
    context_nA: float = .4
    input_nA: float = .8

    def __post_init__(self):
        for name, lo, hi in [('extra_delay_ms', 0, 60), ('relay_gain', 0, 1.5),
                             ('inhibition_gain', 0, 2), ('context_nA', 0, .8), ('input_nA', .1, 1.)]:
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
                raise ValueError(f'{name} is outside its course bounds.')
        if self.extra_delay_ms / DT != round(self.extra_delay_ms / DT):
            raise ValueError('Delay must align with the 0.5 ms grid.')


def build_network(weights, protocol=Protocol()):
    weights = np.asarray(weights, dtype=float)
    if weights.shape != (len(FEATURES), 2) or not np.isfinite(weights).all() or np.any((weights < LOW) | (weights > HIGH)):
        raise ValueError('Invalid 100-cell readout weights.')
    edges = []
    for i, source in enumerate(FEATURES):
        for label, targets in enumerate(OUTPUTS):
            for target in targets:
                edges.append(Synapse(source, target, float(weights[i, label]), 1.))
    # Zero-gain links are absent in the controlled copy; source input is identical.
    if protocol.relay_gain:
        for symbol in range(3):
            for tap in range(16):
                edges.append(Synapse(18 + symbol, 21 + symbol * 16 + tap, 1.2 * protocol.relay_gain, 1. + 5 * tap))
        for source in range(21):
            targets = (69 + source % 12,) if source < 18 else tuple(range(69 + (source-18)*4, 73 + (source-18)*4))
            for target in targets:
                edges.append(Synapse(source, target, 1.05 * protocol.relay_gain, 2.))
    for source in range(69, 81):
        edges.append(Synapse(source, 69 + (source-68) % 12, .035, 3.))
        edges.append(Synapse(source, 81 + (source-69) % 6, .65, 1.))
    if protocol.inhibition_gain:
        for source in range(81, 87):
            for target in (69 + (source-81)*2, 70 + (source-81)*2, 95 + (source-81) % 4):
                edges.append(Synapse(source, target, -.12 * protocol.inhibition_gain, 1.))
    for source in range(95, 99):
        for target in range(95, 99):
            if source != target: edges.append(Synapse(source, target, .04, 2.))
    return Network(100, tuple(edges), inhibitory_neurons=tuple(range(81, 87)))


def source_current(signal, protocol):
    readout = signal.readout_ms + protocol.extra_delay_ms
    duration = readout + 20
    drive = np.zeros((round(duration / DT), 100))
    pulses = []
    if signal.kind == 'pattern':
        pulses.extend((2*i+bit, signal.onset_ms, protocol.input_nA) for i, bit in enumerate(signal.content))
    else:
        pulses.extend((18+'ABC'.index(symbol), signal.onset_ms+i*signal.gap_ms, protocol.input_nA)
                      for i, symbol in enumerate(signal.content))
    pulses.extend((i, signal.onset_ms, protocol.context_nA) for i in range(95, 99))
    pulses.append((99, readout-10, .8))
    for neuron, start, amplitude in pulses:
        first = round(start / DT)
        drive[first:first+10, neuron] += amplitude
    return drive, pulses, readout


def kernel_features(times, cells, readout):
    feature = np.zeros(len(FEATURES))
    lookup = {cell:i for i, cell in enumerate(FEATURES)}
    for time, cell in zip(times, cells):
        age = readout - (float(time) + 1.)
        if int(cell) in lookup and age > 0:
            feature[lookup[int(cell)]] += 100 / 3 * (math.exp(-age/20)-math.exp(-age/5))
    return feature


class RegionModel:
    def __init__(self, seed=7):
        if type(seed) is not int or not 0 <= seed < 2**32: raise ValueError('Invalid seed.')
        self.seed = seed
        self.beta = np.random.default_rng(seed).normal(0, .0002, len(FEATURES))
        self.presentations = 0
        self.history = []

    @property
    def weights(self): return np.column_stack((BASE+self.beta/2, BASE-self.beta/2))

    def clone(self): return copy.deepcopy(self)

    def fingerprint(self): return hashlib.sha256(self.weights.astype('<f8').tobytes()).hexdigest()

    def json_bytes(self):
        return json.dumps({'format':'synapse-region-model-v1', 'seed':self.seed, 'neurons':100,
            'beta_nA':self.beta.tolist(), 'presentations':self.presentations, 'history':self.history,
            'scope':'Fixed spiking encoder, supervised voltage readout. No anatomical region simulation.'},
            indent=2, allow_nan=False).encode()

    @classmethod
    def from_bytes(cls, data):
        if not isinstance(data,bytes) or len(data)>256*1024: raise ValueError('Model JSON must be at most 256 KiB.')
        try:
            value = json.loads(data)
            if value['format']!='synapse-region-model-v1' or value['neurons']!=100: raise ValueError('Wrong model profile.')
            obj = cls(value['seed'])
            beta = np.asarray(value['beta_nA'],dtype=float)
            if beta.shape!=(len(FEATURES),) or not np.isfinite(beta).all() or np.any(np.abs(beta)>HIGH-LOW):
                raise ValueError('Invalid readout strengths.')
            count,history = value['presentations'],value['history']
            if type(count) is not int or not 0<=count<=16384 or not isinstance(history,list) or len(history)>512:
                raise ValueError('Invalid teaching history.')
            consumed = 0
            for row in history:
                if row['kind'] not in ('pattern','sequence') or row['condition'] not in ('teaching','disabled','shuffled'):
                    raise ValueError('Invalid teaching condition.')
                epochs = row['epochs']
                if type(epochs) is not int or not 1<=epochs<=64 or type(row['presentations']) is not int or row['presentations']!=epochs*32:
                    raise ValueError('Invalid teaching count.')
                update = row['update_l2_nA']
                if type(update) not in (int,float) or not math.isfinite(update) or update<0: raise ValueError('Invalid update measurement.')
                consumed += row['presentations']
            if consumed!=count: raise ValueError('History and presentation counts disagree.')
            obj.beta=beta.copy();obj.presentations=count;obj.history=copy.deepcopy(history)
            return obj
        except (KeyError,TypeError,ValueError,OverflowError,AttributeError) as exc:
            raise ValueError(f'100-cell model was not restored: {exc}') from exc


def probe(model, signal, protocol=Protocol(), *, record=False):
    if not isinstance(model, RegionModel) or not isinstance(signal, Signal) or not isinstance(protocol, Protocol):
        raise ValueError('Expected a region model, signal and protocol.')
    if type(record) is not bool: raise ValueError('record must be boolean.')
    drive, pulses, readout = source_current(signal, protocol)
    network = build_network(model.weights, protocol)
    engine = ContinuingNetwork(network, dt_ms=DT)
    cut = round(readout / DT)
    with engine.record_transmissions() as events:
        first = engine.advance(readout, drive[:cut], record=record)
        scores = np.array([engine.voltage[list(ids)].mean()+65 for ids in OUTPUTS])
        second = engine.advance(20, drive[cut:], record=record)
    times = np.concatenate((first.spike_times_ms, second.spike_times_ms))
    cells = np.concatenate((first.spike_neurons, second.spike_neurons))
    if np.isin(cells, OUTPUTS).any(): raise ValueError('Readout left the passive regime; choose weaker input.')
    features = kernel_features(times, cells, readout)
    if not np.allclose(features @ model.weights, scores, atol=3e-10, rtol=0):
        raise ValueError('Measured readout disagrees with independent passive response.')
    margin = float(scores[0]-scores[1])
    return {'prediction':None if abs(margin)<.01 else int(margin<0), 'scores_mV':scores.tolist(),
            'margin_mV':margin, 'features':features, 'readout_ms':readout, 'signal':signal,
            'protocol':protocol, 'network':network, 'pulses':pulses, 'weight_sha256':model.fingerprint(),
            'window':ActivityWindow.from_blocks(-1, [first, second], engine.weights, engine.weights, events) if record else None,
            'spikes':np.column_stack((times, cells)).tolist(),
            'active_cells':int(len(np.unique(cells))), 'spike_count':len(times)}


def evaluate(model, task, protocol=Protocol()):
    rows = []
    for signal, expected in examples(task, test=True):
        result = probe(model, signal, protocol)
        rows.append({'content':''.join(map(str, signal.content)), 'expected':expected,
                     'prediction':result['prediction'], 'margin_mV':result['margin_mV']})
    return {'correct':sum(r['prediction']==r['expected'] for r in rows),
            'abstained':sum(r['prediction'] is None for r in rows), 'total':len(rows), 'rows':rows}


def teach(model, task, *, epochs=32, condition='teaching'):
    if not isinstance(model, RegionModel) or not isinstance(task, Task): raise ValueError('Expected model and task.')
    if type(epochs) is not int or not 1 <= epochs <= 64 or condition not in ('teaching', 'disabled', 'shuffled'):
        raise ValueError('Invalid teaching settings.')
    if model.presentations + epochs*32 > 16384: raise ValueError('Teaching budget reached. Reset or export this model.')
    # No output feedback: cached source-spike features are exact for this encoder.
    data = examples(task)
    feature = np.repeat(np.array([probe(model, s)['features'] for s, _ in data]), 2, axis=0)
    labels = np.repeat([label for _, label in data], 2)
    teachers = labels if condition != 'shuffled' else np.tile([0, 1], len(data))
    before = model.beta.copy()
    beta = before.copy()
    target = .8*(1-2*teachers)
    for _ in range(epochs):
        if condition != 'disabled':
            error = target-feature @ beta
            beta = np.clip(beta + .7*np.mean(feature*(error/(np.sum(feature*feature,axis=1)+1e-12))[:,None],axis=0), -(HIGH-LOW), HIGH-LOW)
    model.beta = beta
    row = {'kind':task.kind, 'condition':condition, 'epochs':epochs, 'presentations':epochs*32,
           'update_l2_nA':float(np.linalg.norm(beta-before))}
    model.presentations += row['presentations']
    model.history.append(row)
    return row.copy()


def controlled_teaching(model, task, *, epochs=32, condition='teaching'):
    """Equal starting weights, inputs and budgets; only update condition differs."""
    before = evaluate(model, task)
    chosen, frozen = model.clone(), model.clone()
    update = teach(chosen, task, epochs=epochs, condition=condition)
    teach(frozen, task, epochs=epochs, condition='disabled')
    return chosen, {'before':before, 'chosen':evaluate(chosen, task), 'disabled':evaluate(frozen, task),
                    'update':update, 'control_unchanged':frozen.fingerprint()==model.fingerprint(),
                    'starting_sha256':model.fingerprint(), 'final_sha256':chosen.fingerprint()}
