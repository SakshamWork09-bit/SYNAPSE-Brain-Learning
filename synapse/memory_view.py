"""Frozen memory-probe display data; no teachers or inference in the browser."""

from dataclasses import asdict
from pathlib import Path
import json
import numpy as np
from .memory_lab import FEATURE_CELLS,OUTPUTS,DT,MIN_MARGIN_MV,build_network

ASSETS=Path(__file__).resolve().parents[1]/'ui_assets'


def payload(model,result=None):
    network=build_network(model.weights)
    groups=[{'name':'Pixel OFF / ON','ids':list(range(18)),'color':'#73cfca'},
            {'name':'A / B / C input','ids':list(range(18,21)),'color':'#efbf78'},
            {'name':'A delay taps','ids':list(range(21,29)),'color':'#91b8df'},
            {'name':'B delay taps','ids':list(range(29,37)),'color':'#b2a3e5'},
            {'name':'C delay taps','ids':list(range(37,45)),'color':'#d7a7c8'},
            {'name':'Response A','ids':[45,46],'color':'#73cfca'},
            {'name':'Response B','ids':[47,48],'color':'#b2a3e5'},
            {'name':'Bias pulse','ids':[49],'color':'#efbf78'}]
    positions=[[.12+.045*(i%2),.1+.075*(i//2)] for i in range(18)]
    positions += [[.12+.07*i,.88] for i in range(3)]
    positions += [[.39+.044*(i%8),.2+.23*(i//8)] for i in range(24)]
    positions += [[.84+.05*(i%2),.34+.28*(i//2)] for i in range(4)]+[[.84,.88]]
    base={'format':'synapse-memory-replay-v1','ready':result is not None,'kind':model.kind,'n':50,
          'seed':model.seed,'presentations':model.presentations,'weight_sha256':model.fingerprint(),
          'groups':groups,'positions':positions,'rest':-65,'threshold':-50,'dt':DT,'minimumMargin':MIN_MARGIN_MV,
          'edges':[{'source':e.source,'target':e.target,'delay':e.delay_ms,'plastic':i<172} for i,e in enumerate(network.synapses)],
          'weights':[e.weight_nA for e in network.synapses],'spikes':[],'arrivals':[],'voltage':[],
          'duration':100,'readoutTime':None,'signal':None,'pulses':[],'prediction':None,'scores':None}
    if result:
        w=result['window']
        if w is None or result['weight_sha256']!=model.fingerprint():raise ValueError('recorded probe must match the model snapshot')
        base.update({'duration':result['signal'].duration_ms,'readoutTime':result['signal'].readout_ms,
                     'signal':asdict(result['signal']),'pulses':result['pulses'],'prediction':result['prediction'],
                     'scores':result['scores_mV'],'margin':result['margin_mV'],
                     'voltage':np.round(w.voltage_mV,5).tolist(),
                     'spikes':np.column_stack((w.spike_times_ms,w.spike_neurons)).tolist(),
                     'arrivals':np.column_stack((w.arrival_times_ms,w.arrival_synapses,w.arrival_weights_nA)).tolist()})
    return base


def html(data):
    from .biology_context import embed
    raw=json.dumps(data,separators=(',',':'),allow_nan=False).replace('<','\\u003c')
    view = ((ASSETS/'memory.html').read_text(encoding='utf-8')
            .replace('__MEMORY_CSS__',(ASSETS/'arena.css').read_text(encoding='utf-8')+'\n'+(ASSETS/'memory.css').read_text(encoding='utf-8'))
            .replace('__MEMORY_CORE__',(ASSETS/'memory_core.js').read_text(encoding='utf-8'))
            .replace('__MEMORY_UI__',(ASSETS/'memory_ui.js').read_text(encoding='utf-8'))
            .replace('__MEMORY_DATA__',raw))
    return embed(view,'memory',data)
