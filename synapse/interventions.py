"""Paired frozen probes of the actual neural engine, isolated from the live session."""

from dataclasses import dataclass,asdict
from io import BytesIO,StringIO
import csv
import hashlib
import json
import math

import numpy as np

from .continuing import ContinuingNetwork
from .laboratory import ActivityWindow
from .network import MAX_TRACE_VALUES
from .continuing import MAX_TOTAL_TICKS

KINDS=('connections','stimulus')


@dataclass(frozen=True)
class ProbeConfig:
    kind: str = 'connections'
    neurons: tuple[int,...] = (0,1,2,3,4)
    amplitude_nA: float = .8
    pulse_start_ms: float = 5.0
    pulse_width_ms: float = 5.0
    duration_ms: float = 100.0
    edges: tuple[int,...] = ()
    edge_gain: float = 1.0
    inhibitory_gain: float = 1.0
    initial_state: str = 'current'

    def __post_init__(self):
        if self.kind not in KINDS or self.initial_state not in ('current','resting'):
            raise ValueError('unsupported probe kind or initial state')
        for name in ('neurons','edges'):
            v=getattr(self,name)
            if not isinstance(v,tuple) or any(type(i) is not int or i<0 for i in v) or len(set(v))!=len(v):
                raise ValueError(f'{name} must contain unique nonnegative integer indices')
        if not 1<=len(self.neurons)<=20:
            raise ValueError('select one to twenty stimulated neurons')
        values=(self.amplitude_nA,self.pulse_start_ms,self.pulse_width_ms,self.duration_ms,self.edge_gain,self.inhibitory_gain)
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
            raise ValueError('probe parameters must be finite numbers')
        if not -1<=self.amplitude_nA<=1 or not 20<=self.duration_ms<=200:
            raise ValueError('pulse amplitude must be in [-1,1] nA and duration in [20,200] ms')
        if self.pulse_start_ms<0 or not 0<self.pulse_width_ms<=50 or self.pulse_start_ms+self.pulse_width_ms>self.duration_ms:
            raise ValueError('pulse must fit inside the probe, with width <=50 ms')
        if not 0<=self.edge_gain<=2 or not 0<=self.inhibitory_gain<=2:
            raise ValueError('manual gains must lie in [0,2]')
        if self.kind=='stimulus' and (self.edges or self.edge_gain!=1 or self.inhibitory_gain!=1):
            raise ValueError('stimulus comparisons cannot also change connection gains')


@dataclass(frozen=True)
class ProbeBranch:
    name: str
    window: ActivityWindow
    input_nA: np.ndarray
    gains: np.ndarray
    spike_counts: np.ndarray
    final_engine_state: dict


@dataclass(frozen=True)
class ProbeResult:
    configuration: ProbeConfig
    source_sha256: str
    source_time_ms: float
    source_engine_state: dict
    initial_engine_state: dict
    control: ProbeBranch
    intervention: ProbeBranch

    def summary(self):
        return {'format':'synapse-intervention-result-v1','configuration':asdict(self.configuration),
                'source_sha256':self.source_sha256,'source_time_ms':self.source_time_ms,
                'probe_time_start_ms':float(self.control.window.time_ms[0]),
                'learning':'Frozen: no outcome feedback or weight updates in either branch.',
                'branches':{b.name:{'spikes':int(b.spike_counts.sum()),'active_neurons':int(np.count_nonzero(b.spike_counts)),
                    'spikes_by_neuron':b.spike_counts.tolist(),
                    'arrivals':len(b.window.arrival_times_ms),
                    'blocked_connections':int(np.count_nonzero(b.gains==0)),
                    'scaled_connections':int(np.count_nonzero(b.gains!=1)),
                    'weights_unchanged':bool(np.array_equal(b.window.initial_weights_nA,b.window.final_weights_nA))}
                    for b in (self.control,self.intervention)},
                'maximum_voltage_difference_mV':float(np.max(np.abs(self.intervention.window.voltage_mV-self.control.window.voltage_mV))),
                'maximum_synaptic_current_difference_nA':float(np.max(np.abs(self.intervention.window.synaptic_current_nA-self.control.window.synaptic_current_nA)))}

    def json_bytes(self,source_context=None):
        return json.dumps({**self.summary(),'source_context':source_context or {},
                           'source_engine_state':self.source_engine_state,
                           'initial_engine_state':self.initial_engine_state},indent=2,allow_nan=False).encode()

    def npz_bytes(self):
        values={}
        for b in (self.control,self.intervention):
            values.update({b.name+'_'+k:v for k,v in vars(b.window).items()})
            values[b.name+'_external_current_nA']=b.input_nA
            values[b.name+'_transmission_gains']=b.gains
        out=BytesIO();np.savez_compressed(out,**values);return out.getvalue()

    def neuron_csv(self):
        out=StringIO(newline='');writer=csv.writer(out)
        writer.writerow(['neuron','control_spikes','intervention_spikes','control_peak_mV','intervention_peak_mV'])
        for i in range(len(self.control.spike_counts)):
            writer.writerow([i,int(self.control.spike_counts[i]),int(self.intervention.spike_counts[i]),
                             float(self.control.window.voltage_mV[:,i].max()),float(self.intervention.window.voltage_mV[:,i].max())])
        return out.getvalue().encode('utf-8')


def edge_presets(network):
    tests={'Sensory A → association A':lambda e:0<=e.source<5 and 10<=e.target<20,
           'Sensory B → association B':lambda e:5<=e.source<10 and 20<=e.target<30,
           'Association → action':lambda e:10<=e.source<30 and 40<=e.target<50,
           'All inhibitory connections':lambda e:e.source in network.inhibitory_neurons,
           'Recurrent association connections':lambda e:10<=e.source<30 and 10<=e.target<30}
    return {label:tuple(i for i,e in enumerate(network.synapses) if test(e)) for label,test in tests.items()}


def run_probe(source,config=None):
    if not isinstance(source,ContinuingNetwork):raise ValueError('source must be a continuing neural engine')
    config=config if config is not None else ProbeConfig()
    if not isinstance(config,ProbeConfig):raise ValueError('config must be ProbeConfig')
    n=len(source.voltage);m=len(source.weights)
    if any(i>=n for i in config.neurons) or any(i>=m for i in config.edges):
        raise ValueError('probe neuron or connection index is outside this circuit')
    for t in (config.duration_ms,config.pulse_start_ms,config.pulse_width_ms):
        if not math.isclose(t/source.dt_ms,round(t/source.dt_ms),rel_tol=0,abs_tol=1e-8):
            raise ValueError('probe timing must align with the engine time step')
    source_state=source.state_dict()
    source_hash=hashlib.sha256(json.dumps(source_state,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    initial=source_state
    if config.initial_state=='resting':
        rested=ContinuingNetwork(source.network,dt_ms=source.dt_ms,eligible_synapses=source.selected,
                                reward_parameters=source.reward_parameters)
        rested.weights[:]=source.weights
        rested.tick=source.tick
        initial=rested.state_dict()
    steps=round(config.duration_ms/source.dt_ms)
    if (steps+1)*n>MAX_TRACE_VALUES or source.tick+steps>MAX_TOTAL_TICKS:
        raise ValueError('probe would exceed its recording or engine time budget')
    drive=np.zeros((steps,n))
    first=round(config.pulse_start_ms/source.dt_ms);last=first+round(config.pulse_width_ms/source.dt_ms)
    drive[first:last,list(config.neurons)]=config.amplitude_nA
    candidate_gains=np.ones(m)
    candidate_gains[list(config.edges)]*=config.edge_gain
    for i,e in enumerate(source.network.synapses):
        if e.weight_nA<0:candidate_gains[i]*=config.inhibitory_gain
    branches=[]
    for name in ('control','intervention'):
        engine=ContinuingNetwork.from_state_dict(initial)
        gains=np.ones(m) if name=='control' else candidate_gains
        current=np.zeros_like(drive) if config.kind=='stimulus' and name=='control' else drive.copy()
        before=engine.weights.copy()
        with engine.temporary_transmission_gains(gains),engine.record_transmissions() as events:
            block=engine.advance(config.duration_ms,current,record=True)
        window=ActivityWindow.from_blocks(-1,(block,),before,engine.weights,events)
        branches.append(ProbeBranch(name,window,current,gains.copy(),block.spike_counts,engine.state_dict()))
    # Both snapshots were made on isolated objects, with identical initial state.
    return ProbeResult(config,source_hash,source.time_ms,source_state,initial,*branches)


def rerun_probe_export(data):
    """Reproduce a bounded exported experiment from validated JSON bytes."""
    if not isinstance(data,bytes) or len(data)>10*1024*1024:
        raise ValueError('experiment JSON must be bytes within 10 MiB')
    try:
        value=json.loads(data.decode('utf-8'))
        if value['format']!='synapse-intervention-result-v1':raise ValueError('unsupported experiment format')
        cfg=value['configuration'];cfg={**cfg,'neurons':tuple(cfg['neurons']),'edges':tuple(cfg['edges'])}
        engine=ContinuingNetwork.from_state_dict(value['source_engine_state'])
        digest=hashlib.sha256(json.dumps(engine.state_dict(),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        if digest!=value['source_sha256']:
            raise ValueError('experiment source integrity check failed')
        return run_probe(engine,ProbeConfig(**cfg))
    except (UnicodeDecodeError,json.JSONDecodeError,KeyError,TypeError,OverflowError,RecursionError) as exc:
        raise ValueError('invalid experiment JSON or structure') from exc
