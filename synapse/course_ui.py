"""The main neuroscience learning platform: biology, visualisation, evidence."""

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .course_content import CHAPTERS, CHAPTER_BY_ID, NAV_LABELS, GLOSSARY, SOURCES, source_markdown
from .course_models import (BranchConfig, branch_experiment, branch_payload, neuron_experiment,
                            synapse_experiment, notebook_bytes, load_notebook, notebook_markdown)
from .course_view import explorer_html
from .replay import replay_html, replay_payload
from .laboratory import Laboratory
from .integrated import IntegratedSession
from .guided_view import biology_html
from . import lab_charts as charts


def init():
    st.session_state.setdefault('course_progress', [])
    st.session_state.setdefault('course_notes', {})


def navigate(label):
    st.session_state.workspace = 'Course'
    st.session_state.course_chapter = label
    st.session_state.running = False
    st.session_state.arena_running = False


def _complete(chapter):
    init()
    progress = st.session_state.course_progress
    st.session_state.course_progress = [c['id'] for c in CHAPTERS if c['id'] in progress or c['id'] == chapter['id']]
    index = list(CHAPTERS).index(chapter)
    navigate(CHAPTERS[index+1]['nav'] if index+1 < len(CHAPTERS) else 'My learning notebook')


def _save_and_complete(chapter, note_key):
    st.session_state.course_notes = {**st.session_state.course_notes,
                                    chapter['id']:st.session_state.get(note_key,'')}
    _complete(chapter)


def _plot(fig, key):
    st.plotly_chart(fig, theme=None, width='stretch', key=key,
                    config={'displaylogo':False, 'scrollZoom':False})


def _section(section):
    title, text, sources = section
    st.subheader(title)
    st.write(text)
    if sources: st.caption(source_markdown(sources))


def _scene(kind):
    st.iframe(explorer_html(kind), height='content', tab_index=0,
              alt=f'Interactive {kind} biology illustration, distinct from calculated model recordings')


def _branch(compact=False):
    key = 'course_home_branch' if compact else 'course_network_branch'
    st.markdown('**MODEL RECORDING · 50 NEURONS · 690 CONNECTIONS**')
    if compact:
        config = BranchConfig()
        if st.button('Launch a signal', key='course_home_launch', type='primary'):
            st.session_state[key] = branch_experiment(config)
    else:
        st.markdown('### Launch a signal through the branching circuit')
        st.write('Start with a pulse to group A. Then reduce its pathway transmission and compare '
                 'with a copy receiving the identical pulse. Learning is frozen in both copies.')
        with st.form('course_branch_form'):
            cols = st.columns(2)
            cue = cols[0].radio('Input group', [0, 1], format_func=lambda v:'A' if v == 0 else 'B', horizontal=True, key='course_branch_cue')
            amplitude = cols[1].slider('Pulse strength (nA)', 0.0, 1.0, .8, .05, key='course_branch_amplitude')
            pathway = cols[0].slider('Input → association transmission', 0.0, 2.0, 1.0, .1, key='course_branch_gain')
            inhibition = cols[1].slider('Inhibitory transmission', 0.0, 2.0, 1.0, .1, key='course_branch_inhibition')
            st.caption('Gain 1 keeps transmission unchanged; 0 blocks the selected links. These gains are experimental settings, not learned changes.')
            if st.form_submit_button('Launch and compare', type='primary', width='stretch'):
                config = BranchConfig(amplitude, pathway, inhibition, cue)
                st.session_state[key] = branch_experiment(config)
                st.session_state[key+'_config'] = config
    result = st.session_state.get(key)
    branch = 'intervention'
    if result is not None:
        s = result.summary()['branches']
        cols = st.columns(3)
        cols[0].metric('Control · active neurons', s['control']['active_neurons'])
        cols[1].metric('Changed copy · active neurons', s['intervention']['active_neurons'])
        cols[2].metric('Changed copy · spikes', s['intervention']['spikes'])
        if not compact:
            cfg = st.session_state[key+'_config']
            st.caption(f'RECORDED SETTINGS · input {"A" if cfg.cue == 0 else "B"} · {cfg.amplitude_nA:g} nA · '
                       f'pathway gain {cfg.pathway_gain:g} · inhibitory gain {cfg.inhibition_gain:g}. '
                       'Form edits affect the next calculation, not this recording.')
            branch = st.radio('Inspect matched recording', ['intervention', 'control'],
                format_func=lambda v:'Your changed copy' if v=='intervention' else 'Control copy',
                horizontal=True, key='course_branch_recording')
    st.iframe(replay_html(branch_payload(result, branch)), height='content', tab_index=0,
              alt='Calculated branching circuit with actual spikes, transmissions and neuron inspection')
    st.caption('The visible groups are an engineered arrangement. They are not mapped onto actual brain lobes. '
               'The moving points are signal markers; the drawing is not an anatomical reconstruction.')
    if result is not None and not compact:
        st.download_button('Download this controlled circuit experiment', result.json_bytes({'course':'networks'}),
            'synapse_course_network.json', 'application/json', key='course_network_export', on_click='ignore')


def _home():
    st.markdown('<div class="eyebrow">SYNAPSE / AN INTERACTIVE JOURNEY INTO THE HUMAN BRAIN</div>', unsafe_allow_html=True)
    st.title('From a brain to a cell. From a signal to learning.')
    st.write('Learn the biology, look inside the mechanism, and investigate a small model. '
             'Follow the chapters in order or choose a question that interests you.')
    cols = st.columns(3)
    cols[0].metric('Connected chapters', len(CHAPTERS))
    cols[1].metric('Chapters you marked explored', len(st.session_state.course_progress))
    cols[2].metric('Scales to explore', 'Organ · cell · circuit')
    st.caption('Explored marks record your own progress; they are not assessed knowledge scores.')
    _branch(compact=True)
    st.markdown('### Your learning journey')
    for row in (CHAPTERS[:3], CHAPTERS[3:]):
        cols = st.columns(3)
        for col, c in zip(cols, row):
            with col, st.container(border=True):
                st.caption('CHAPTER '+c['number']+(' · EXPLORED' if c['id'] in st.session_state.course_progress else ''))
                st.subheader(c['title'])
                st.write(c['question'])
                st.button('Explore chapter →', key='course_open_'+c['id'], on_click=navigate, args=(c['nav'],), width='stretch')
    with st.expander('How to use this platform'):
        st.write('Biology illustrations explain structures and mechanisms. Model recordings replay '
                 'calculated values from simplified circuits. Read their connection to biology and '
                 'their limits together. Click structures, pause sequences, inspect signals, change '
                 'one condition and write a short reflection. Download your notebook to retain progress.')
        st.caption('This is an initial six-chapter course, not a complete neuroscience textbook. '
                   'References distinguish textbook explanations, animal/culture experiments and human studies.')


def _signals():
    _scene('voltage')
    with st.expander('Under the membrane · chemical and electrical forces'):
        st.write('Diffusion tends to move an ion down its concentration gradient, while voltage '
                 'can attract or repel that ion. At its equilibrium potential these influences '
                 'balance. For a single ion, the Nernst relation expresses this balance:')
        st.latex(r'E_{\mathrm{ion}}=\frac{RT}{zF}\ln\left(\frac{[\mathrm{ion}]_{\mathrm{outside}}}{[\mathrm{ion}]_{\mathrm{inside}}}\right)')
        st.caption('R: gas constant; T: absolute temperature; z: ion valence; F: Faraday constant. '
                   'Use consistent concentration units. Multiple permeant ions contribute to a real '
                   'resting membrane potential, so it is not generally equal to one ion’s Nernst potential.')
        st.caption(source_markdown(['forces','rest']))
    st.markdown('### Investigate a calculated neuron')
    st.write('Change the external input. Compare it with a fresh copy receiving no added current. '
             'Both use the same membrane parameters and start at rest.')
    value = st.slider('Input during 20–180 ms (nA)', 0.0, .6, .25, .01, key='course_neuron_current')
    if st.button('Calculate the response', type='primary', key='course_neuron_run'):
        st.session_state.course_neuron_result = (value, neuron_experiment(value), neuron_experiment(0.0))
    saved = st.session_state.get('course_neuron_result')
    if saved is None:
        st.info('Calculate once to see measured voltage and spike events. The illustration above remains a schematic.')
        return
    recorded, result, control = saved
    st.caption(f'MODEL RECORDING · {recorded:g} nA input · 200 ms window · 0.2 ms step')
    if recorded != value: st.info('The slider has changed; calculate again to replace the previous recording.')
    cols = st.columns(3)
    cols[0].metric('Chosen input · spikes', len(result.spike_times_ms))
    cols[1].metric('No added input · spikes', len(control.spike_times_ms))
    cols[2].metric('Model threshold', '−50 mV')
    fig = go.Figure()
    for r, label, color in [(control,'No added input','#829aaa'),(result,'Chosen input',charts.CYAN)]:
        fig.add_trace(go.Scatter(x=r.time_ms,y=r.voltage_mV,mode='lines',name=label,line=dict(color=color)))
    fig.add_hline(y=-50, line_dash='dash',line_color=charts.ORANGE)
    fig.add_trace(go.Scatter(x=result.spike_times_ms,y=np.full(len(result.spike_times_ms),-50),
                            mode='markers',name='Spike events · not waveform peaks',marker=dict(color=charts.LILAC,size=8)))
    _plot(charts.finish(fig,x='Calculated time (ms)',y='Model membrane voltage (mV)'), 'course_neuron_chart')
    st.write('The recorded trace integrates and leaks, then resets when a spike event occurs. '
             'Markers indicate those events at the threshold; they do not add a simulated biological spike shape.')


def _synapses():
    st.iframe(biology_html(), height='content', tab_index=0, alt='Step-by-step chemical-synapse illustration')
    st.markdown('### Send one signal and inspect the receiving voltage')
    weight = st.slider('Signed model connection strength (nA)', -.3, .3, .1, .01, key='course_synapse_weight')
    st.caption('Positive values add excitatory current; negative values add hyperpolarising current. '
               'This model does not calculate receptor conductances or shunting inhibition.')
    if st.button('Send one signal', key='course_synapse_run', type='primary'):
        st.session_state.course_synapse_result = (weight, synapse_experiment(weight), synapse_experiment(0.0))
    saved = st.session_state.get('course_synapse_result')
    if saved is None: return
    recorded, result, control = saved
    st.caption(f'MODEL RECORDING · strength {recorded:+g} nA · only A receives an external pulse · learning absent')
    if recorded != weight: st.info('Strength has changed; send a new signal to replace the previous recording.')
    cols = st.columns(3)
    cols[0].metric('A spikes', int(result.spike_counts[0]))
    cols[1].metric('B spikes', int(result.spike_counts[1]))
    effect = result.voltage_mV[:,1]+65
    extreme = float(np.max(effect) if recorded >= 0 else np.min(effect))
    cols[2].metric('B · largest signed deviation', f'{extreme:+.4f} mV')
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=control.time_ms,y=control.voltage_mV[:,1]+65,name='No connection',line=dict(color='#829aaa')))
    fig.add_trace(go.Scatter(x=result.time_ms,y=effect,name='B response',line=dict(color=charts.CYAN)))
    _plot(charts.finish(fig,x='Calculated time (ms)',y='B voltage above rest (mV)'), 'course_synapse_chart')
    st.write('A fired, but B stayed below threshold at these bounded strengths. '
             'The response can be positive, negative or absent; receiving an event is different from emitting a spike.')


def _interference():
    st.markdown('### When new associations disturb old ones')
    st.write('This controlled engineering analogy compares new-only teaching with interleaved '
             'old/new teaching. It measures familiar class associations at reserved timings, '
             'rather than recognition of genuinely new drawings.')
    kind = st.radio('Association example', ['pattern', 'sequence'],
        format_func=lambda k:'Small drawings' if k=='pattern' else 'Timed sequences', horizontal=True,key='course_memory_kind')
    if st.button('Compare old and new associations', type='primary', key='course_memory_run'):
        from .memory_lab import MemoryModel, Task, teach, interference, SECOND_PATTERNS
        old = Task.defaults(kind)
        new = Task(kind, SECOND_PATTERNS if kind=='pattern' else (tuple('BABC'),tuple('ABBC')))
        model = MemoryModel(kind, 7)
        with st.spinner('Teaching the old task and calculating two matched teaching schedules…'):
            teach(model, old, epochs=32)
            result, _, _ = interference(model, old, new, epochs=32)
        st.session_state.course_interference = (kind, result)
    saved = st.session_state.get('course_interference')
    if saved:
        recorded, result = saved
        st.caption(f'RECORDED ASSOCIATION PROFILE · {recorded} · equal added teaching budgets: '
                   f"{result['new_presentations']} / {result['rehearsal_presentations']} presentations")
        if recorded != kind: st.info('The example type has changed. Run again to replace the previous result.')
        rows=[]
        for key,label in [('before','Before new teaching'),('new_only','New-only teaching'),('rehearsal','Interleaved teaching')]:
            rows.append({'Schedule':label, 'Old associations matched':f"{result[key]['old']['origin_correct']} / 16",
                         'New associations matched':f"{result[key]['new']['origin_correct']} / 16"})
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        st.caption('This profile uses a fixed encoder and a supervised readout rule, separate from pair-STDP. '
                   'Rehearsal can fail on competing tasks. Supplied examples do not simulate biological sleep.')


def _learning():
    with st.expander('Inside a biological synapse · an example of molecular plasticity'):
        st.write('At some hippocampal glutamatergic synapses, NMDA receptors combine ligand and '
                 'voltage dependence. Glutamate and a co-agonist enable activation, while sufficient '
                 'depolarisation relieves magnesium block. Calcium entry can then recruit intracellular signalling.')
        st.write('In forms of potentiation, calcium/calmodulin-dependent kinase II (CaMKII) and '
                 'changes in AMPA receptor function or trafficking contribute to stronger transmission. '
                 'Longer-lasting changes can also involve protein synthesis and structural processes. '
                 'Mechanisms vary by synapse and protocol; these molecular steps are not calculated '
                 'by our additive weight rule.')
        st.caption(source_markdown(['nmda','molecular']))
    timing, interference_tab = st.tabs(['At a connection: timing and retained effects', 'Across tasks: interference'])
    with timing:
        from .guided_ui import _experiment, _evidence
        _experiment(embedded=True)
        if 'guided_experiment' in st.session_state:
            with st.expander('Compare the evidence and frozen transmission probes', expanded=True):
                _evidence(embedded=True)
    with interference_tab: _interference()


def _behaviour():
    if 'course_choice_lab' not in st.session_state:
        st.session_state.course_choice_lab = Laboratory(IntegratedSession(7))
    lab = st.session_state.course_choice_lab
    st.markdown('### Follow a cue, a choice and its consequence')
    st.write('Use one experience first. Watch input activity, the selected button and later feedback '
             'in the branching recording. Advance a batch to inspect repeated experience.')
    cols = st.columns(3)
    if cols[0].button('Run one experience', type='primary', key='course_choice_one', disabled=lab.remaining==0): lab.advance(1)
    if cols[1].button('Run 20 experiences', key='course_choice_twenty', disabled=lab.remaining==0):
        with st.spinner('Calculating experience and retaining the newest recordings…'): lab.advance(20)
    if cols[2].button('Reset this choice model', key='course_choice_reset'):
        st.session_state.course_choice_lab = Laboratory(IntegratedSession(7))
        st.rerun()
    data = replay_payload(lab.session,lab.windows[-1] if lab.windows else None)
    data['course']={'title':'Input. Neural activity. Action. Consequence.',
        'intro':'A separate two-choice model. The outcome follows the action; the recorded signals and changes are calculated.',
        'explanation':'Sensory cells receive an engineered cue. At 25 ms the decoder chooses from neural voltages and exploration. '
                      'The chosen action is then executed. Feedback arrives at 35 ms and can change eligible links. '
                      'These times are protocol choices, not measured timings of human decisions. Columns show model roles, not brain areas.'}
    st.iframe(replay_html(data),height='content',tab_index=0,alt='Recorded branching activity in a cue-action-feedback loop')
    records = lab.session.records
    if records:
        recent = records[-20:]
        st.write(f"**{len(records)} experiences calculated.** Successful choices in the last {len(recent)}: "
                 f"**{sum(r['reward'] for r in recent)} / {len(recent)}**.")
        st.caption('This is online success while learning and exploration continue. It is not a held-out accuracy '
                   'or a human cognitive score. The experiment reverses its cue rule after experience 100.')
    with st.expander('Go further: a simulated movement environment'):
        st.write('This optional activity uses a separate four-action model and engineered direction/obstacle '
                 'sensors. It is a simulation of agent–environment interaction, not a model of human vision '
                 'or the detailed motor system. Read the biological explanation above alongside its limits.')
        from .arena_ui import page as arena_page
        arena_page(embedded=True)


def _footer(chapter):
    title, text, sources = chapter['deep']
    with st.expander('Go deeper · '+title):
        st.write(text)
        if sources: st.caption(source_markdown(sources))
    st.success(chapter['takeaway'])
    with st.expander('Sources and what the model represents'):
        for key in chapter['sources']:
            label,url=SOURCES[key]
            st.markdown(f'- [{label}]({url})')
        st.caption('Textbook descriptions introduce mechanisms. Primary studies specify their preparation and task. '
                   'The illustrations are original schematics. Numerical recordings are outputs of simplified models, '
                   'not measurements from a human brain. Expert/learner review has not yet been completed.')
    st.markdown('### Put it in your own words')
    st.write(chapter['reflection'])
    note_key = 'course_reflection_'+chapter['id']
    with st.form('course_note_'+chapter['id']):
        note = st.text_area('My reflection',value=st.session_state.course_notes.get(chapter['id'],''),
                            max_chars=10000,key=note_key,placeholder='Explain the mechanism, what you observed, and one limit of the model.')
        if st.form_submit_button('Save my reflection'):
            st.session_state.course_notes = {**st.session_state.course_notes,chapter['id']:note}
            st.success('Reflection saved in this session. Download your notebook to keep it after closing the app.')
        st.form_submit_button('Save and mark explored →',type='primary',key='course_continue_'+chapter['id'],
                              on_click=_save_and_complete,args=(chapter,note_key))
    st.caption('This marks your own progress; it does not certify mastery.')


def _chapter(chapter):
    st.markdown(f"<div class='eyebrow'>CHAPTER {chapter['number']} / HUMAN BRAIN LEARNING JOURNEY</div>",unsafe_allow_html=True)
    st.title(chapter['title'])
    st.markdown('### '+chapter['question'])
    st.info(chapter['relatable'])
    with st.expander('What you will be able to explain'):
        for goal in chapter['goals']: st.write('• '+goal)
    sections = chapter['sections']
    if chapter['id']=='brain':
        _section(sections[0]);_scene('brain');_section(sections[1]);_scene('neuron');_section(sections[2])
    else:
        for section in sections: _section(section)
        {'signals':_signals,'synapses':_synapses,'networks':_branch,'learning':_learning,'behaviour':_behaviour}[chapter['id']]()
    _footer(chapter)


def _glossary():
    st.title('A language for understanding the brain')
    st.write('Look up a word without losing the distinction between a biological mechanism and a model parameter.')
    search = st.text_input('Find a term or idea',key='course_glossary_search').strip().lower()
    matches = [(term,definition,source) for term,(definition,source) in GLOSSARY.items()
               if search in term.lower() or search in definition.lower()]
    if not matches: st.info('No matching term yet. Try “synapse”, “voltage”, “memory” or “model”.')
    for term,definition,source in matches:
        with st.container(border=True):
            st.subheader(term);st.write(definition)
            if source: st.caption(source_markdown([source]))


def _notebook():
    st.title('Your learning notebook')
    st.write('Keep your reflections and self-marked progress. These notes do not store or restore model weights.')
    for c in CHAPTERS:
        with st.expander(c['number']+' · '+c['title'], expanded=bool(st.session_state.course_notes.get(c['id']))):
            st.caption('Marked explored' if c['id'] in st.session_state.course_progress else 'Not marked explored')
            st.write(st.session_state.course_notes.get(c['id']) or 'No reflection saved yet.')
            st.button('Return to chapter',key='course_note_return_'+c['id'],on_click=navigate,args=(c['nav'],))
    cols=st.columns(2)
    cols[0].download_button('Download readable notebook',notebook_markdown(st.session_state.course_progress,st.session_state.course_notes),
        'synapse_learning_notebook.md','text/markdown',on_click='ignore',key='course_notebook_md',width='stretch')
    cols[1].download_button('Download notebook to restore later',notebook_bytes(st.session_state.course_progress,st.session_state.course_notes),
        'synapse_learning_notebook.json','application/json',on_click='ignore',key='course_notebook_json',width='stretch')
    upload=st.file_uploader('Restore a course notebook · up to 256 KiB',type=['json'],key='course_notebook_upload')
    if st.button('Restore learning notebook',disabled=upload is None,key='course_notebook_restore'):
        try:
            progress,notes=load_notebook(upload.getvalue())
            st.session_state.course_progress=progress;st.session_state.course_notes=notes
            st.session_state.course_notebook_restored=True;st.rerun()
        except ValueError as exc: st.error(str(exc))
    if st.session_state.pop('course_notebook_restored',False): st.success('Learning notebook restored.')


def page():
    from .regions_ui import page as regional_course
    regional_course()
