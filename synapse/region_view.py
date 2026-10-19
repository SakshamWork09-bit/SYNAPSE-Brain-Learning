"""Offline anatomical plates and synchronized measured-circuit playback."""

import base64
import json
from pathlib import Path

import numpy as np

from .region_content import ATLAS, LESSON_BY_ID, SOURCES, task_stages
from .region_model import GROUPS, DT, source_current
from .query_report import compare_input

ASSETS = Path(__file__).resolve().parents[1] / 'ui_assets'


def asset_uri(name):
    path = ASSETS / 'anatomy' / name
    mime = 'image/svg+xml' if path.suffix == '.svg' else 'image/png'
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode()


def _plates():
    return {
        'lateral':dict(title='Cortical surface · anterior at right', image=asset_uri('brain_regions.png'),
                       width=815, height=568, note='Lateral view. The V1 cortex extends onto the medial surface. The motor and prefrontal markers indicate subregions of the frontal lobe.'),
        'medial':dict(title='Medial section · anterior at right', image=asset_uri('brain_medial.png'),
                      width=540, height=488, note='Sagittal teaching section. Markers locate thalamus, hypothalamus and brainstem approximately; they do not outline nuclei.'),
        'hippocampus':dict(title='Medial-temporal structures · anterior at left', image=asset_uri('hippocampus.png'),
                           width=825, height=588, note='Different orientation: anterior is at left. The plate exposes paired medial-temporal structures. Hippocampal bodies and anterior amygdalae are marked approximately.'),
        'deep':dict(title='Deep structures · coronal teaching section', image=asset_uri('brain_section.png'),
                    width=436, height=390, note='An approximate basal-ganglia location in a coronal teaching section; the halo is not a segmentation of individual nuclei.'),
    }


def payload(result=None, lesson_id='pfc', *, task=None):
    if lesson_id not in LESSON_BY_ID: raise ValueError('Unknown regional lesson.')
    lesson = LESSON_BY_ID[lesson_id]
    data = {'format':'synapse-region-replay-v1', 'ready':result is not None, 'neurons':100,
            'lesson':lesson_id, 'lessonTitle':lesson['title'], 'plates':_plates(), 'atlas':ATLAS,
            'sources':{k:{'label':v[0], 'url':v[1]} for k,v in SOURCES.items()},
            'groups':[dict(id=id, name=name, cells=list(cells), color=color, detail=detail)
                      for id,name,cells,color,detail in GROUPS],
            'scope':'The anatomical halos are source-backed interpretations of task demands, not calculated or measured human regional activity. The circuit has 100 identical LIF cells arranged by engineering role; no group stands for a brain region.',
            'coordination':lesson['coordination'], 'cellular':lesson['cellular'], 'limits':lesson['limits'],
            'time':[], 'voltage':[], 'current':[], 'input':[], 'spikes':[], 'arrivals':[], 'edges':[],
            'stages':[], 'duration':0, 'readout':0, 'prediction':None, 'scores':[], 'learningDuringRecording':False}
    if result is None: return data
    if task is not None: data['queryComparison']=compare_input(result['signal'],task)
    window = result['window']
    if window is None: raise ValueError('Replay needs a recorded probe.')
    network = result['network']
    if network.n_neurons != 100: raise ValueError('Expected the 100-cell teaching circuit.')
    data.update(time=window.time_ms.tolist(), voltage=np.round(window.voltage_mV,5).tolist(),
                current=np.round(window.synaptic_current_nA,6).tolist(),
                input=np.round(source_current(result['signal'],result['protocol'])[0],6).tolist(),
                spikes=np.column_stack((window.spike_times_ms, window.spike_neurons)).tolist(),
                arrivals=np.column_stack((window.arrival_times_ms,window.arrival_synapses,window.arrival_weights_nA)).tolist(),
                edges=[dict(source=s.source,target=s.target,weight=s.weight_nA,delay=s.delay_ms) for s in network.synapses],
                duration=float(window.time_ms[-1]), readout=result['readout_ms'], dt=DT,
                prediction=result['prediction'], scores=result['scores_mV'], weightHash=result['weight_sha256'],
                signal=dict(kind=result['signal'].kind,content=list(result['signal'].content),onset=result['signal'].onset_ms,gap=result['signal'].gap_ms),
                stages=task_stages(lesson_id,result['signal'],result['readout_ms']))
    return data


def replay_html(data):
    if data.get('format') != 'synapse-region-replay-v1': raise ValueError('Wrong replay format.')
    raw = json.dumps(data, allow_nan=False, separators=(',',':')).replace('<','\\u003c')
    return ((ASSETS/'region.html').read_text(encoding='utf-8')
            .replace('__REGION_CSS__',(ASSETS/'region.css').read_text(encoding='utf-8'))
            .replace('__REGION_CORE__',(ASSETS/'region_core.js').read_text(encoding='utf-8'))
            .replace('__REGION_UI__',(ASSETS/'region_ui.js').read_text(encoding='utf-8'))
            .replace('__REGION_DATA__',raw))


def anatomy_html(lesson_id='pfc'):
    return replay_html(payload(None,lesson_id))
