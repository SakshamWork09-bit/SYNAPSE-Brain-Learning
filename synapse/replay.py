"""Build self-contained recorded-event playback; never selects or rewards an action."""

import json
from pathlib import Path
import numpy as np

from .integrated import GROUPS
from .laboratory import GROUP_COLORS, GROUP_LABELS
from .continuing import ContinuingNetwork

ASSETS=Path(__file__).resolve().parents[1]/'ui_assets'


def _graph_data(engine,seed,mode,exploration):
    if engine.network.n_neurons!=50:
        raise ValueError('this grouped replay requires the 50-neuron profile')
    groups=[{'name':name,'color':color,'neurons':list(ids)}
            for name,color,ids in zip(GROUP_LABELS,GROUP_COLORS,GROUPS.values())]
    edges=[{'source':e.source,'target':e.target,'delay':e.delay_ms,'plastic':i in engine.selected}
           for i,e in enumerate(engine.network.synapses)]
    data={'format':'synapse-recorded-replay-v1','groups':groups,'edges':edges,'n':50,
          'rest':engine.network.neuron.rest_mV,'threshold':engine.network.neuron.threshold_mV,
          'mode':mode,'seed':seed,'exploration':exploration}
    return data


def replay_payload(session,window=None):
    engine=session.engine
    data=_graph_data(engine,session.seed,session.mode,session.config.exploration)
    data['ready']=window is not None
    if window is None:
        data.update({'initialWeights':engine.weights.tolist(),'initialVoltage':engine.voltage.tolist(),
                     'spikes':[],'arrivals':[],'duration':100})
        return data
    row=session.records[window.trial]
    start=float(window.time_ms[0])
    data.update({'trial':window.trial+1,'absoluteStart':start,'duration':100,
                 'dt':session.config.dt_ms,'initialWeights':window.initial_weights_nA.tolist(),
                 'finalWeights':window.final_weights_nA.tolist(),
                 'voltage':np.round(window.voltage_mV,4).tolist(),
                 'spikes':np.column_stack((window.spike_times_ms-start,window.spike_neurons)).tolist(),
                 'arrivals':np.column_stack((window.arrival_times_ms-start,window.arrival_synapses,
                                            window.arrival_weights_nA)).tolist(),
                 'cue':int(row['cue']),'action':int(row['action']),
                 'scores':np.asarray(row['action_scores_mV'],dtype=float).tolist(),
                 'probabilities':np.asarray(row['action_probabilities'],dtype=float).tolist(),
                 'reward':int(row['reward']),'feedback':float(row['delivered_feedback']),
                 'decisionTime':25,'feedbackTime':35,'phase':int(row['phase'])})
    return data


def probe_payload(result,branch='intervention',seed=None):
    if branch not in ('control','intervention'):
        raise ValueError('select control or intervention')
    engine=ContinuingNetwork.from_state_dict(result.initial_engine_state)
    b=getattr(result,branch);w=b.window;start=float(w.time_ms[0]);cfg=result.configuration
    data=_graph_data(engine,seed,'frozen_probe',0)
    effective=w.initial_weights_nA*b.gains
    amplitude=0.0 if cfg.kind=='stimulus' and branch=='control' else cfg.amplitude_nA
    data.update({'ready':True,'kind':'probe','branch':branch,'duration':cfg.duration_ms,
                 'absoluteStart':start,'dt':engine.dt_ms,'manualGains':b.gains.tolist(),
                 'initialWeights':effective.tolist(),'finalWeights':effective.tolist(),
                 'voltage':np.round(w.voltage_mV,4).tolist(),
                 'spikes':np.column_stack((w.spike_times_ms-start,w.spike_neurons)).tolist(),
                 'arrivals':np.column_stack((w.arrival_times_ms-start,w.arrival_synapses,w.arrival_weights_nA)).tolist(),
                 'stimulus':{'neurons':list(cfg.neurons),'amplitude':amplitude,
                             'start':cfg.pulse_start_ms,'stop':cfg.pulse_start_ms+cfg.pulse_width_ms},
                 'decisionTime':None,'feedbackTime':None})
    return data


def replay_html(payload):
    """Inline assets and escape JSON so a saved replay runs offline."""
    from .biology_context import embed
    data=json.dumps(payload,separators=(',',':'),allow_nan=False).replace('<','\\u003c')
    template=(ASSETS/'replay.html').read_text(encoding='utf-8')
    view = (template.replace('__REPLAY_CSS__',(ASSETS/'replay.css').read_text(encoding='utf-8'))
                    .replace('__REPLAY_CORE__',(ASSETS/'replay_core.js').read_text(encoding='utf-8'))
                    .replace('__REPLAY_UI__',(ASSETS/'replay_ui.js').read_text(encoding='utf-8'))
                    .replace('__REPLAY_DATA__',data))
    return embed(view,'choice',payload)
