"""Attach a synchronized, explicitly interpretive anatomy panel to earlier tools."""

import json

from .region_content import ATLAS, SOURCES
from .region_view import asset_uri


def embed(html, profile, data):
    if profile not in ('memory','arena','choice'): raise ValueError('Unknown biology context.')
    if profile=='memory':
        signal=data.get('signal') or {}
        onset=signal.get('onset_ms',10.)
        last=onset+max(0,len(signal.get('content',[]))-1)*signal.get('gap_ms',20.)+5 if data.get('kind')=='sequence' else onset+5
        readout=data.get('readoutTime') or 80
        stages=[(0,onset,'Prepare a task',['pfc','parietal'],'Frontal–parietal interactions contribute to task control and selection. The model instead receives a preset input schedule.',['human_wm','parietal_human']),
            (onset,last,'Encode a visible signal',['occipital','temporal'],'A human viewing patterns or written symbols uses visual pathways and object-related representations. This model receives pixel/symbol currents directly.',['visual_streams','what_where']),
            (last,readout,'Use recent evidence',['pfc','temporal'],'A biological sequence task can use distributed control and memory networks. The engineered circuit preserves recent input with fixed delay lines and decaying currents.',['pfc_cells','human_wm']),
            (readout,data.get('duration',100)+1,'Read a class response',['pfc','motor'],'Responding in a real task can recruit selection and motor systems. Here a software decoder compares class voltages; the weights remain frozen.',['motor_cells','human_wm'])]
    elif profile=='arena':
        stages=[(0,5,'Observe the environment',['parietal','pfc'],'Spatial and goal-related information contributes to real action. The arena supplies engineered direction and obstacle sensors; it has no human visual pathway.',['parietal','premotor']),
            (5,20,'Select a move',['pfc','parietal'],'Frontoparietal planning interacts with other selection systems. This controller reads action-cell voltages and may explore before the outcome is available.',['parietal_human','premotor']),
            (20,35,'Execute an action',['motor','cerebellum'],'Biological execution involves descending motor pathways and cerebellar interactions. The arena chooses a grid move rather than simulating muscles or Purkinje cells.',['motor_cells','cerebellar_outputs']),
            (35,101,'Use a consequence',['pfc','motor'],'Biological feedback learning involves wider systems, including basal-ganglia circuits. The arena applies a scalar feedback signal to eligible model links; it does not calculate dopamine or a human reward prediction error.',['reward','bg_circuit'])]
        if data.get('lessonFocus')=='cerebellum':
            stages[3]=(35,101,'Relate the outcome to future movement',['cerebellum','motor'],
                'Human cerebellar circuits contribute to adapting movements from sensory prediction errors. '
                'This arena instead returns a scalar consequence to eligible sensor-to-action links. '
                'Compare that feedback with the reach aftereffect above; the arena does not calculate climbing-fibre signals or Purkinje-cell plasticity.',
                ['reach_adaptation','cerebellar_cells','cerebellar_outputs'])
    else:
        probe=data.get('kind')=='probe'
        stages=[(0,5,'External cue',['occipital','pfc'],'For a human viewing a cue, visual and control networks could contribute. Model source cells instead receive an artificial pulse.',['visual_streams','human_wm']),
            (5,25,'Propagation and integration',['pfc','temporal'],'Biological networks combine many inputs through excitation and inhibition. These columns are engineered groups, not brain areas.',['processing','human_wm']),
            (25,35,'Receiving response' if probe else 'Choose and execute',['pfc'] if probe else ['pfc','motor'],'This controlled probe calculates transmission only; it produces no task action or reward.' if probe else 'The model reads neural voltages before the feedback event. Biological selection and execution involve additional interacting systems.',['motor_cells','processing']),
            (35,data.get('duration',100)+1,'Frozen transmission' if probe else 'Later feedback',['pfc'],'The probe keeps learned weights fixed; manual gains are experimental settings.' if probe else 'Scalar model feedback can change eligible links. Biological reward learning involves mechanisms beyond this engineering signal.',['reward','processing'])]
    value={'profile':profile,'ready':data.get('ready',False),'image':asset_uri('brain_regions.png'),
           'atlas':{k:v for k,v in ATLAS.items() if v['view']=='lateral'},
           'stages':[dict(start=a,end=b,title=title,regions=regions,why=why,sources=[dict(label=SOURCES[k][0],url=SOURCES[k][1]) for k in refs])
                     for a,b,title,regions,why,refs in stages]}
    raw=json.dumps(value,separators=(',',':'),allow_nan=False).replace('<','\\u003c')
    section='''<section class="syn-biology"><div class="syn-bio-image"><img id="syn-bio-plate" alt="Servier Medical Art lateral brain diagram; anterior at right"><div id="syn-bio-halos"></div></div><div><div class="syn-bio-kicker">BIOLOGICAL INTERPRETATION / SYNCHRONISED WITH THIS RECORDING</div><h3 id="syn-bio-title"></h3><p id="syn-bio-why"></p><p id="syn-bio-sources"></p><small>Halos mark approximate locations, not measured activity or anatomical borders. Engineered neuron groups do not represent these regions. Diagram: <a href="https://smart.servier.com/smart_image/brain-area/" target="_blank" rel="noopener noreferrer">Servier Medical Art</a>, <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>; interactive markers added.</small></div></section>'''
    css='''<style>.syn-biology{font:13px/1.5 system-ui,sans-serif;color:#203e48;background:#edf4ef;border:1px solid #cadbd4;border-radius:12px;max-width:1400px;margin:12px auto;padding:16px;display:grid;grid-template-columns:215px 1fr;gap:20px}.syn-biology h3{font-size:17px;margin:5px 0 8px}.syn-biology p{margin:6px 0}.syn-biology small,.syn-biology #syn-bio-sources{font-size:11px;color:#526c75}.syn-bio-kicker{font-size:10px;letter-spacing:.1em;color:#126d70}.syn-bio-image{position:relative;align-self:center;aspect-ratio:815/568}.syn-bio-image img{width:100%;height:100%;object-fit:contain}.syn-bio-image i{position:absolute;border:2px solid #126d70;background:#e9b64a55;border-radius:50%;transform:translate(-50%,-50%)}.syn-biology a{color:#126d70}@media(max-width:650px){.syn-biology{grid-template-columns:1fr;margin:8px}.syn-bio-image{max-width:230px;width:100%;margin:auto}}</style>'''
    script='''<script>(()=>{const d=JSON.parse(document.getElementById('syn-biology-data').textContent),$=id=>document.getElementById(id);let last=-1;$('syn-bio-plate').src=d.image;window.updateSynapseBiology=time=>{const index=d.stages.findIndex(s=>time>=s.start&&time<s.end);if(index===last)return;last=index;const s=d.stages[index]||d.stages[0];$('syn-bio-title').textContent=d.ready?s.title+' · '+s.regions.map(k=>d.atlas[k].name).join(' / '):'Calculate an experience to follow a task stage';$('syn-bio-why').textContent=d.ready?s.why:'This anatomical panel explains a biological connection to the task. It follows the recording clock after a calculation.';$('syn-bio-halos').replaceChildren();if(d.ready)s.regions.forEach(k=>{const r=d.atlas[k],halo=document.createElement('i');halo.style.left=(r.x*100)+'%';halo.style.top=(r.y*100)+'%';halo.style.width=(2*r.r*100)+'%';halo.style.height=(2*r.r*815/568*100)+'%';halo.title=r.name;$('syn-bio-halos').appendChild(halo);});$('syn-bio-sources').replaceChildren();s.sources.forEach((ref,i)=>{if(i)$('syn-bio-sources').appendChild(document.createTextNode(' · '));const a=document.createElement('a');a.textContent=ref.label;a.href=ref.url;a.target='_blank';a.rel='noopener noreferrer';$('syn-bio-sources').appendChild(a);});};window.updateSynapseBiology(0);})();</script>'''
    return html.replace('<body>','<body>'+css+section+'<script id="syn-biology-data" type="application/json">'+raw+'</script>'+script,1)
