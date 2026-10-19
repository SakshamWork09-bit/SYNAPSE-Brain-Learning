"""Original, self-contained SVG teaching illustrations, distinct from model data."""

import json
from pathlib import Path

from .course_content import REGIONS

ASSETS = Path(__file__).resolve().parents[1] / 'ui_assets'

SCENES = {
    'brain': {'title':'Explore the brain at two depths', 'parts':REGIONS,
              'foot':'Approximate orientation diagrams. Left: outer surface, front to the left. Right: simplified medial cutaway. Deep structures are not drawn on the outer surface. Functions depend on connected systems; boundaries are simplified.'},
    'neuron': {'title':'Follow the structure of a neuron', 'parts':[
        {'id':'dendrites','name':'Dendrites','detail':'Branching processes receive many synaptic inputs. This is a schematic multipolar neuron; real cells have varied shapes.'},
        {'id':'soma','name':'Cell body','detail':'The soma contains the nucleus and much of the machinery that maintains the cell.'},
        {'id':'initial','name':'Initial segment','detail':'In many neurons this excitable region initiates an action potential when conditions permit.'},
        {'id':'axon','name':'Axon','detail':'An action potential is regenerated along excitable membrane. The moving highlight marks a conceptual signal, not a particle travelling the entire axon.'},
        {'id':'myelin','name':'Myelin and nodes','detail':'Myelin insulates portions of the axon. Nodes between segments provide sites where spikes can be regenerated.'},
        {'id':'terminals','name':'Axon terminals','detail':'The axon can branch to contact several targets. These contacts can influence multiple receiving cells.'}],
        'foot':'Biology illustration of a typical multipolar neuron, not to scale. The sequence is explanatory artwork; propagation speed, ionic currents and anatomical dimensions are not calculated.'},
    'voltage': {'title':'Step through an action potential', 'parts':[
        {'id':'rest','name':'1 · Rest','detail':'Selective permeability and maintained ion gradients support a resting membrane potential. This illustrated cell starts near −70 mV.'},
        {'id':'rise','name':'2 · Depolarisation','detail':'Voltage-dependent sodium conductance rises rapidly. Sodium entry can drive the membrane toward a more positive potential.'},
        {'id':'fall','name':'3 · Repolarisation','detail':'Sodium channels inactivate while potassium conductance increases. Potassium efflux helps the voltage become negative again.'},
        {'id':'after','name':'4 · After-hyperpolarisation','detail':'Potassium conductance can remain elevated briefly. The membrane can become more negative than its resting level.'},
        {'id':'recover','name':'5 · Recovery','detail':'Channel states recover and the membrane returns toward its resting condition. Absolute and relative refractory phases affect whether another spike can occur.'}],
        'foot':'Schematic voltage curve, not measured data or a channel simulation. Voltages and phase spacing illustrate one typical example; human neuronal waveforms vary. The LIF experiment below uses threshold/reset instead.'},
}


def explorer_html(kind):
    if kind not in SCENES: raise ValueError('Unknown biology illustration.')
    data = json.dumps({'kind':kind, **SCENES[kind]}, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    return ((ASSETS / 'course_explorer.html').read_text(encoding='utf-8')
            .replace('__COURSE_CSS__', (ASSETS / 'course_explorer.css').read_text(encoding='utf-8'))
            .replace('__COURSE_DATA__', data)
            .replace('__COURSE_JS__', (ASSETS / 'course_explorer.js').read_text(encoding='utf-8')))
