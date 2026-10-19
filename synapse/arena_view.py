"""Read-only arena playback payload and self-contained HTML."""

import json
import copy
from pathlib import Path
import numpy as np
from .arena import SENSOR_NAMES, ACTIONS

ASSETS = Path(__file__).resolve().parents[1]/'ui_assets'


def arena_payload(session, *, lesson_focus=None):
    if lesson_focus not in (None,'cerebellum','motor'): raise ValueError('Unknown movement lesson focus.')
    profile=session.profile
    sensors,motors,inhibitory=profile.sensors,profile.motors,profile.inhibitory
    window = session.last_window
    row = copy.deepcopy(session.records[-1]) if window is not None else None
    trail = [list(session.episode_start)] if session.episode_start is not None else []
    if session.episode_steps:
        trail += [list(r['after']) for r in session.records[-session.episode_steps:]]
    if row is not None: trail = trail[:-1]
    groups = [{'name':name,'ids':list(ids),'color':'#73cfca' if i<4 else '#efa679'}
              for i,(name,ids) in enumerate(zip(SENSOR_NAMES,sensors))]
    groups += [{'name':name+' action','ids':list(ids),'color':'#a99bea'} for name,ids in zip(ACTIONS,motors)]
    groups += [{'name':'Inhibition','ids':list(inhibitory),'color':'#e69a73'}]
    positions = []
    for i,ids in enumerate(sensors):
        positions += [[.12+.055*(j%3),.09+i*.115+.035*(j//3)] for j in range(len(ids))]
    columns=3 if profile.n_neurons==50 else 5
    horizontal=.045 if profile.n_neurons==50 else .035
    for i,ids in enumerate(motors):
        positions += [[.60+horizontal*(j%columns),.17+i*.21+.045*(j//columns)] for j in range(len(ids))]
    columns=2 if profile.n_neurons==50 else 3
    base,horizontal,vertical=(.88,.045,.09) if profile.n_neurons==50 else (.86,.035,.055)
    positions += [[base+horizontal*(j%columns),.38+vertical*(j//columns)] for j in range(len(inhibitory))]
    weights = window.initial_weights_nA if window is not None else session.engine.weights
    return {'format':'synapse-arena-replay-v1','ready':row is not None,'seed':session.seed,'mode':session.mode,
            'world':{'walls':[list(x) for x in session.world.walls],'hazards':[list(x) for x in session.world.hazards]},
            'goal':list(session.goal) if session.goal is not None else None,
            'position':row['before'] if row is not None else list(session.position) if session.position is not None else None,
            'trail':trail,'row':row,'duration':100,'dt':session.engine.dt_ms,'n':profile.n_neurons,
            'lessonFocus':lesson_focus,'adaptiveCount':len(session.engine.selected),
            'groups':groups,'positions':positions,'rest':session.engine.network.neuron.rest_mV,
            'threshold':session.engine.network.neuron.threshold_mV,
            'edges':[{'source':e.source,'target':e.target,'delay':e.delay_ms,'plastic':i in session.engine.selected}
                     for i,e in enumerate(session.engine.network.synapses)],
            'initialWeights':weights.tolist(),
            'finalWeights':window.final_weights_nA.tolist() if window is not None else weights.tolist(),
            'voltage':np.round(window.voltage_mV,4).tolist() if window is not None else [],
            'spikes':np.column_stack((window.spike_times_ms-window.time_ms[0],window.spike_neurons)).tolist() if window is not None else [],
            'arrivals':np.column_stack((window.arrival_times_ms-window.time_ms[0],window.arrival_synapses,window.arrival_weights_nA)).tolist() if window is not None else []}


def arena_html(payload):
    from .biology_context import embed
    text = json.dumps(payload,separators=(',',':'),allow_nan=False).replace('<','\\u003c')
    view = ((ASSETS/'arena.html').read_text(encoding='utf-8')
            .replace('__ARENA_CSS__',(ASSETS/'arena.css').read_text(encoding='utf-8'))
            .replace('__ARENA_CORE__',(ASSETS/'arena_core.js').read_text(encoding='utf-8'))
            .replace('__ARENA_UI__',(ASSETS/'arena_ui.js').read_text(encoding='utf-8'))
            .replace('__ARENA_N__',str(payload['n']))
            .replace('__ARENA_LINKS__',str(len(payload['edges'])))
            .replace('__ARENA_ADAPTIVE__',str(sum(bool(e['plastic']) for e in payload['edges'])))
            .replace('__ARENA_DATA__',text))
    return embed(view,'arena',payload)
