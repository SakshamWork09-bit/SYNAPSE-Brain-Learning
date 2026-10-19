"""Two-class pattern association and short fading-memory sequence experiments.

Fixed spiking delay lines encode history. A supervised normalized delta rule
trains positive readout synapses between presentations, not during frozen probes.
"""

from dataclasses import dataclass,asdict
import copy
import hashlib
import json
import math

import numpy as np

from .continuing import ContinuingNetwork
from .network import Network,Synapse
from .laboratory import ActivityWindow

FEATURE_CELLS=tuple(range(18))+tuple(range(21,45))+(49,)
OUTPUTS=((45,46),(47,48))
DT=.5
LOW,HIGH=.002,.020
BASE=(LOW+HIGH)/2
MAX_PRESENTATIONS=8192
MIN_MARGIN_MV=.01
DEFAULT_PATTERNS=((1,0,0,1,0,0,1,1,1),(1,1,1,0,1,0,0,1,0))
SECOND_PATTERNS=((1,1,1,0,1,0,0,1,1),(1,1,0,1,0,0,1,1,1))


@dataclass(frozen=True)
class Signal:
    kind: str
    content: tuple
    onset_ms: float=10.0
    gap_ms: float=20.0

    def __post_init__(self):
        if self.kind not in ('pattern','sequence') or not isinstance(self.content,tuple):raise ValueError('unsupported signal')
        if self.kind=='pattern':
            if len(self.content)!=9 or any(type(x) is not int or x not in (0,1) for x in self.content):
                raise ValueError('patterns need nine binary pixels')
        elif not 2<=len(self.content)<=6 or any(x not in ('A','B','C') for x in self.content):
            raise ValueError('sequences need two to six A/B/C symbols')
        for x,lo,hi in ((self.onset_ms,8,16),(self.gap_ms,12,30)):
            if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not lo<=x<=hi or x/DT!=round(x/DT):
                raise ValueError('onset 8..16 ms and spacing 12..30 ms must use 0.5 ms steps')

    @property
    def readout_ms(self):return 40.0 if self.kind=='pattern' else self.onset_ms+(len(self.content)-1)*self.gap_ms+50

    @property
    def duration_ms(self):return self.readout_ms+20

    @classmethod
    def from_dict(cls,value):
        if not isinstance(value,dict):raise ValueError('invalid signal JSON')
        try:return cls(value['kind'],tuple(value['content']),value['onset_ms'],value['gap_ms'])
        except (KeyError,TypeError) as exc:raise ValueError('invalid signal JSON') from exc


def sequence(text,onset=10.,gap=20.):
    if not isinstance(text,str):raise ValueError('type a sequence of A/B/C symbols')
    return Signal('sequence',tuple(''.join(text.upper().split())),onset,gap)


@dataclass(frozen=True)
class Task:
    kind: str
    prototypes: tuple

    def __post_init__(self):
        if not isinstance(self.prototypes,tuple) or len(self.prototypes)!=2:raise ValueError('two class prototypes required')
        for p in self.prototypes:Signal(self.kind,p)
        if self.prototypes[0]==self.prototypes[1]:raise ValueError('classes need different signals')

    @classmethod
    def defaults(cls,kind='pattern'):
        return cls(kind,DEFAULT_PATTERNS if kind=='pattern' else (tuple('ABBA'),tuple('BABA')))

    @classmethod
    def from_dict(cls,value):
        try:return cls(value['kind'],tuple(tuple(x) for x in value['prototypes']))
        except (KeyError,TypeError) as exc:raise ValueError('invalid task JSON') from exc


def build_network(weights):
    edges=[]
    for k,source in enumerate(FEATURE_CELLS):
        for label,targets in enumerate(OUTPUTS):
            for target in targets:edges.append(Synapse(source,target,float(weights[k,label]),1.))
    for symbol in range(3):
        for tap in range(8):edges.append(Synapse(18+symbol,21+symbol*8+tap,1.2,1.+10*tap))
    return Network(50,tuple(edges))


def source_current(signal):
    current=np.zeros((round(signal.duration_ms/DT),50))
    pulses=[]
    if signal.kind=='pattern':
        for pixel,bit in enumerate(signal.content):pulses.append((2*pixel+bit,signal.onset_ms))
    else:
        pulses.extend((18+'ABC'.index(symbol),signal.onset_ms+i*signal.gap_ms) for i,symbol in enumerate(signal.content))
    pulses.append((49,signal.readout_ms-10))
    for neuron,start in pulses:
        first=round(start/DT);current[first:first+10,neuron]+=.8
    return current,pulses


def kernel_features(times,cells,readout):
    """Exact passive output voltage sensitivity per nA, from actual source spikes."""
    features=np.zeros(len(FEATURE_CELLS));lookup={cell:i for i,cell in enumerate(FEATURE_CELLS)}
    for time,neuron in zip(times,cells):
        age=readout-(float(time)+1.)
        if int(neuron) in lookup and age>0:
            features[lookup[int(neuron)]]+=100*5/(20-5)*(math.exp(-age/20)-math.exp(-age/5))
    return features


class MemoryModel:
    def __init__(self,kind='pattern',seed=7):
        if kind not in ('pattern','sequence') or type(seed) is not int or not 0<=seed<2**32:raise ValueError('invalid memory profile or seed')
        self.kind,self.seed=kind,seed
        self.beta=np.random.default_rng(seed).normal(0,.0002,len(FEATURE_CELLS))
        self.presentations=0
        self.history=[]

    @property
    def weights(self):return np.column_stack((BASE+self.beta/2,BASE-self.beta/2))

    def clone(self):return copy.deepcopy(self)

    def fingerprint(self):return hashlib.sha256(self.weights.astype('<f8').tobytes()).hexdigest()

    def payload(self):
        return {'format':'synapse-memory-model-v1','kind':self.kind,'seed':self.seed,
                'beta_nA':self.beta.tolist(),'presentations':self.presentations,'history':copy.deepcopy(self.history),
                'rule':'Supervised normalized delta on exact passive voltage features; bounds 0.002..0.020 nA.',
                'readout':'Mean LIF class voltages at signal readout; no teachers, prototypes or updates in inference.'}

    def json_bytes(self):
        value=self.payload();canonical=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        return json.dumps({'format':'synapse-memory-checkpoint-v1','sha256':hashlib.sha256(canonical).hexdigest(),'payload':value},allow_nan=False).encode()

    @classmethod
    def from_bytes(cls,data):
        if not isinstance(data,bytes) or len(data)>2*1024*1024:raise ValueError('model file must be JSON bytes within 2 MiB')
        try:
            outer=json.loads(data);value=outer['payload']
            canonical=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            if outer['format']!='synapse-memory-checkpoint-v1' or hashlib.sha256(canonical).hexdigest()!=outer['sha256'] or value['format']!='synapse-memory-model-v1':
                raise ValueError('unsupported model or integrity mismatch')
            obj=cls(value['kind'],value['seed']);beta=np.asarray(value['beta_nA'],dtype=float)
            if beta.shape!=(43,) or not np.isfinite(beta).all() or np.any(np.abs(beta)>HIGH-LOW):raise ValueError('invalid readout strengths')
            total=value['presentations'];history=value['history']
            if type(total) is not int or not 0<=total<=MAX_PRESENTATIONS or not isinstance(history,list) or len(history)>64:raise ValueError('invalid teaching history')
            consumed=0
            for row in history:
                if (type(row['presentations']) is not int or row['presentations']<1 or row['presentations']%16 or row['condition'] not in ('teaching','disabled','shuffled')
                    or not math.isfinite(row['update_l2_nA']) or row['update_l2_nA']<0):raise ValueError('invalid teaching history entry')
                consumed+=row['presentations']
            if consumed!=total:raise ValueError('history/presentation mismatch')
            obj.beta=beta.copy();obj.presentations=total;obj.history=copy.deepcopy(history)
            return obj
        except (KeyError,TypeError,ValueError,OverflowError,AttributeError) as exc:raise ValueError(f'invalid memory model: {exc}') from exc


def probe(model,signal,*,record=False):
    if not isinstance(model,MemoryModel) or not isinstance(signal,Signal) or model.kind!=signal.kind:raise ValueError('signal and model profiles must match')
    if type(record) is not bool:raise ValueError('record must be a boolean')
    drive,pulses=source_current(signal)
    engine=ContinuingNetwork(build_network(model.weights),dt_ms=DT)
    blocks=[]
    cut=round(signal.readout_ms/DT)
    with engine.record_transmissions() as events:
        first=engine.advance(signal.readout_ms,drive[:cut],record=record);blocks.append(first)
        scores=np.array([engine.voltage[list(ids)].mean()+65 for ids in OUTPUTS])
        second=engine.advance(20,drive[cut:],record=record);blocks.append(second)
    times=np.concatenate([b.spike_times_ms for b in blocks]);cells=np.concatenate([b.spike_neurons for b in blocks])
    if np.isin(cells,(45,46,47,48)).any():raise ValueError('output spiked; this task requires passive voltage readout')
    features=kernel_features(times,cells,signal.readout_ms)
    # A mathematical identity of this feedforward, subthreshold readout, checked on every probe.
    if not np.allclose(features@model.weights,scores,atol=2e-10,rtol=0):raise ValueError('passive voltage feature identity failed')
    margin=float(scores[0]-scores[1]);prediction=None if abs(margin)<MIN_MARGIN_MV else int(margin<0)
    window=ActivityWindow.from_blocks(-1,blocks,engine.weights,engine.weights,events) if record else None
    return {'prediction':prediction,'scores_mV':scores.tolist(),'margin_mV':margin,'features':features,
            'window':window,'pulses':pulses,'signal':signal,'weight_sha256':model.fingerprint()}


def examples(task,*,test=False,noise=0,seed=10007):
    if not isinstance(task,Task) or type(noise) is not int or not 0<=noise<=2 or type(seed) is not int or not 0<=seed<2**32:raise ValueError('invalid evaluation settings')
    rng=np.random.default_rng(seed);rows=[]
    for label,p in enumerate(task.prototypes):
        for i in range(8):
            content=list(p)
            if noise:
                for j in rng.choice(len(p),min(noise,len(p)),replace=False):
                    content[j]=1-content[j] if task.kind=='pattern' else str(rng.choice([v for v in 'ABC' if v!=content[j]]))
            onset=(12 if test else 8)+i*.5
            gap=18+(i%4)+(0.5 if test else 0)
            signal=Signal(task.kind,tuple(content),onset,gap)
            rows.append((signal,label))
    return tuple(rows)


def teach(model,task,*,epochs=32,condition='teaching',seed=7,additional=None):
    if not isinstance(model,MemoryModel) or not isinstance(task,Task) or model.kind!=task.kind:raise ValueError('matching model and task required')
    if type(epochs) is not int or not 1<=epochs<=64 or condition not in ('teaching','disabled','shuffled'):
        raise ValueError('use 1..64 epochs and a supported teaching condition')
    if additional is not None and (not isinstance(additional,Task) or additional.kind!=task.kind):raise ValueError('invalid rehearsal task')
    if type(seed) is not int or not 0<=seed<2**32:raise ValueError('invalid teaching seed')
    data=list(examples(task))
    if additional is not None:data+=list(examples(additional))
    count=epochs*len(data)*2
    if model.presentations+count>MAX_PRESENTATIONS or len(model.history)>=64:raise ValueError('model teaching budget reached')
    # Fixed encoder has no feedback from output cells: cache its actual spike-derived features.
    basis=MemoryModel(model.kind,model.seed)
    features=np.array([probe(basis,s)['features'] for s,_ in data])
    labels=np.repeat([label for _,label in data],2);rng=np.random.default_rng(seed)
    features=np.repeat(features,2,axis=0)
    teachers=labels.copy()
    if condition=='shuffled':
        # Each exact signal receives both teachers. Every condition repeats each
        # signal twice, preserving identical input and presentation budgets.
        teachers=np.array([teacher for _ in data for teacher in rng.permutation([0,1])])
    old=model.beta.copy();beta=old.copy()
    margins=[]
    for epoch in range(epochs):
        target=.8*(1-2*teachers)
        if condition!='disabled':
            error=target-features@beta
            beta=np.clip(beta+.7*(features.T@(error/(np.sum(features*features,axis=1)+1e-12)))/len(labels),-(HIGH-LOW),HIGH-LOW)
        margins.append(float(np.mean((features@beta)*(1-2*labels))))
    result={'condition':condition,'presentations':count,'distinct_training_signals':len(data),'epochs':epochs,
            'update_l2_nA':float(np.linalg.norm(beta-old)),'mean_signed_margin_by_epoch_mV':margins,
            'teacher_counts':[int(np.count_nonzero(teachers==i)) for i in (0,1)],
            'true_counts':[int(np.count_nonzero(labels==i)) for i in (0,1)],
            'teaching_seed':seed,'rehearsal':additional is not None}
    model.beta=beta;model.presentations+=count;model.history.append(copy.deepcopy(result))
    return result


def distance(content,prototype):
    return abs(len(content)-len(prototype))+sum(a!=b for a,b in zip(content,prototype))


def evaluate(model,task,*,noise=0,seed=10007):
    if model.kind!=task.kind:raise ValueError('task/profile mismatch')
    before=model.fingerprint()
    data=examples(task,test=True,noise=noise,seed=seed);rows=[]
    for signal,label in data:
        p=probe(model,signal)
        ds=[distance(signal.content,x) for x in task.prototypes];ambiguous=ds[0]==ds[1]
        baseline=None if ambiguous else int(ds[1]<ds[0])
        rows.append({'signal':asdict(signal),'origin_label':label,'prediction':p['prediction'],
                     'scores_mV':p['scores_mV'],'margin_mV':p['margin_mV'],
                     'ambiguous_template_distance':ambiguous,'prototype_baseline':baseline})
    valid=[r for r in rows if not r['ambiguous_template_distance']]
    matrix=np.zeros((2,3),dtype=int)
    for row in rows:matrix[row['origin_label'],2 if row['prediction'] is None else row['prediction']]+=1
    return {'format':'synapse-memory-evaluation-v1','kind':task.kind,'task':asdict(task),'noise_changes':noise,
            'test_seed':seed,'weight_sha256':model.fingerprint(),'presentations':model.presentations,
            'cases':len(rows),'origin_correct':sum(r['prediction']==r['origin_label'] for r in rows),
            'abstentions':sum(r['prediction'] is None for r in rows),'minimum_margin_mV':MIN_MARGIN_MV,
            'unambiguous_cases':len(valid),'unambiguous_correct':sum(r['prediction']==r['origin_label'] for r in valid),
            'ambiguous_cases':len(rows)-len(valid),'confusion_matrix':matrix.tolist(),
            'closer_to_other_template':sum(r['prototype_baseline'] is not None and r['prototype_baseline']!=r['origin_label'] for r in rows),
            'prototype_baseline_correct':sum(r['prototype_baseline']==r['origin_label'] for r in valid),
            'unique_contents':len(set(tuple(r['signal']['content']) for r in rows)),
            'rows':rows,'weights_unchanged':model.fingerprint()==before}


def comparison(task,seed=7,epochs=32):
    results={};models={}
    for mode in ('before','teaching','disabled','shuffled'):
        model=MemoryModel(task.kind,seed)
        if mode!='before':teach(model,task,epochs=epochs,condition=mode,seed=seed)
        models[mode]=model
        results[mode]={str(noise):evaluate(model,task,noise=noise) for noise in (0,1,2)}
    return {'format':'synapse-memory-comparison-v1','task':asdict(task),'seed':seed,'epochs':epochs,'conditions':results},models


def interference(model,old_task,new_task,*,epochs=32,seed=7):
    if model.kind!=old_task.kind or model.kind!=new_task.kind:raise ValueError('all interference profiles must match')
    if type(epochs) is not int or not 2<=epochs<=64 or epochs%2:raise ValueError('interference requires even epochs in 2..64 for matched budgets')
    new_only=model.clone();rehearsed=model.clone()
    teach(new_only,new_task,epochs=epochs,seed=seed)
    # Match presentation budgets: each rehearsal epoch contains twice as many samples.
    teach(rehearsed,new_task,epochs=max(1,epochs//2),seed=seed,additional=old_task)
    return {'format':'synapse-memory-interference-v1','old_task':asdict(old_task),'new_task':asdict(new_task),
            'source_weight_sha256':model.fingerprint(),
            'before':{'old':evaluate(model,old_task),'new':evaluate(model,new_task)},
            'new_only':{'old':evaluate(new_only,old_task),'new':evaluate(new_only,new_task)},
            'rehearsal':{'old':evaluate(rehearsed,old_task),'new':evaluate(rehearsed,new_task)},
            'new_presentations':new_only.presentations-model.presentations,
            'rehearsal_presentations':rehearsed.presentations-model.presentations},new_only,rehearsed


def workbench_bytes(task,model,snapshot=None):
    if task.kind!=model.kind or snapshot is not None and snapshot.kind!=task.kind:raise ValueError('workbench profiles differ')
    value={'format':'synapse-memory-workbench-v1','task':asdict(task),
           'model':json.loads(model.json_bytes()),'snapshot':json.loads(snapshot.json_bytes()) if snapshot else None}
    canonical=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return json.dumps({'sha256':hashlib.sha256(canonical).hexdigest(),'payload':value},allow_nan=False).encode()


def load_workbench(data):
    if not isinstance(data,bytes) or len(data)>4*1024*1024:raise ValueError('workbench JSON limit is 4 MiB')
    try:
        outer=json.loads(data);value=outer['payload']
        canonical=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        if value['format']!='synapse-memory-workbench-v1' or hashlib.sha256(canonical).hexdigest()!=outer['sha256']:raise ValueError('workbench integrity mismatch')
        task=Task.from_dict(value['task']);model=MemoryModel.from_bytes(json.dumps(value['model']).encode())
        snapshot=MemoryModel.from_bytes(json.dumps(value['snapshot']).encode()) if value['snapshot'] is not None else None
        if task.kind!=model.kind or snapshot is not None and snapshot.kind!=task.kind:raise ValueError('workbench profile mismatch')
        return task,model,snapshot
    except (KeyError,TypeError,ValueError,OverflowError) as exc:raise ValueError(f'invalid memory workbench: {exc}') from exc
