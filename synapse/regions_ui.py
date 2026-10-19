"""The regional biology course. Experiments belong to their biology lesson."""

import json

import pandas as pd
import streamlit as st

from .region_content import LESSONS, LESSON_BY_ID, NAV_LABELS, source_markdown
from .region_model import RegionModel, Protocol, probe, controlled_teaching, GROUPS, build_network
from .region_view import payload, replay_html, anatomy_html, asset_uri
from .memory_lab import Signal, Task, sequence
from .experience_lab import ACTIVITIES, ExperienceSession
from .query_report import compare_input


def init():
    st.session_state.setdefault('course_progress', [])
    st.session_state.setdefault('course_notes', {})
    st.session_state.setdefault('region_tasks', {})
    if 'region_model' not in st.session_state: st.session_state.region_model = RegionModel()


def navigate(label):
    st.session_state.workspace = 'Course'
    st.session_state.course_chapter = label
    st.session_state.running = st.session_state.arena_running = False
    st.session_state.movement100_running = False


def _view(result=None, lesson_id='pfc', task=None):
    st.iframe(replay_html(payload(result, lesson_id, task=task)), height='content', tab_index=0,
              alt='Sourced medical brain diagrams, task-stage interpretations and a recorded 100-neuron circuit')


def _home():
    st.markdown('<div class="eyebrow">SYNAPSE / A HANDS-ON JOURNEY THROUGH YOUR BRAIN</div>',unsafe_allow_html=True)
    with st.container(key='journey_hero'):
        st.title('Try something. See what changes.')
        st.write('Keep a rule. Adapt a reach. Teach a shape. Explore twelve brain regions through twelve different experiments.')
        st.button('Start with the prefrontal cortex →',type='primary',key='region_start',on_click=navigate,args=(LESSONS[0]['nav'],))
        st.caption('One idea → your experiment → what happened. Open the deeper biology whenever you want.')
    st.subheader('Pick a stop, or follow the numbers')
    for start in range(0, len(LESSONS), 3):
        cols = st.columns(3)
        for col, lesson in zip(cols, LESSONS[start:start+3]):
            with col, st.container(border=True,key='route_'+lesson['id']):
                explored = ' · EXPLORED' if lesson['id'] in st.session_state.course_progress else ''
                st.caption('SECTION '+lesson['number']+explored)
                st.subheader(lesson['title'])
                st.write(ACTIVITIES[lesson['id']]['title'])
                st.button('Enter section →', key='region_open_'+lesson['id'], on_click=navigate,
                          args=(lesson['nav'],), width='stretch')
    with st.container(border=True):
        st.subheader('Need the cell-level foundations?')
        st.write('Zoom into a neuron, change its input, and follow a signal across a synapse.')
        st.button('Explore cell foundations',key='region_foundations',on_click=navigate,args=('Cell foundations',))
    if st.toggle('Preview the branching 100-neuron workbench',key='region_home_microscope'):
        if st.button('Launch a branching signal', type='primary', key='region_home_launch'):
            s = Signal('sequence', Task.defaults('sequence').prototypes[0], 12.)
            st.session_state.region_home_result = probe(st.session_state.region_model, s, record=True)
        _view(st.session_state.get('region_home_result'))


def _pattern_editor(key, default):
    st.caption('Custom 3 × 3 input · tick a cell to turn its pixel ON')
    values = []
    for row in range(3):
        cols = st.columns(3)
        for col in range(3):
            i = row*3+col
            values.append(int(cols[col].checkbox(f'Row {row+1} · column {col+1}', bool(default[i]), key=f'{key}_{i}')))
    return tuple(values)


def _input(lesson):
    id, kind = lesson['id'], lesson['kind']
    task = st.session_state.region_tasks.get(id,Task.defaults(kind))
    st.subheader('100-neuron microscope · '+lesson['experiment'])
    st.caption('This retained workbench shares its weights across sections. Its recorded spikes describe an engineered circuit; '
               'the activity above has its own settings and state.')
    st.caption('Readout A names Example 1; readout B names Example 2. A class preference is not an exact-match guarantee.')
    with st.expander('Edit Example 1 and Example 2 independently'):
        with st.form('region_examples_'+id):
            cols=st.columns(2)
            values=[]
            for index,col in enumerate(cols):
                with col:
                    st.markdown(f'**Example {index+1}**')
                    key=f'region_example_{id}_{index}'
                    if kind=='pattern': values.append(_pattern_editor(key,task.prototypes[index]))
                    else: values.append(st.text_input(f'Example {index+1} · 2–6 symbols from A, B, C',
                        ''.join(task.prototypes[index]),key=key))
            if st.form_submit_button('Apply these two examples',key='region_apply_examples_'+id):
                try:
                    prototypes=tuple(values) if kind=='pattern' else tuple(sequence(v).content for v in values)
                    task=Task(kind,prototypes)
                    st.session_state.region_tasks={**st.session_state.region_tasks,id:task}
                    st.success('Both examples applied. Existing weights and recordings are preserved; teach to learn this pair.')
                except ValueError as exc: st.error(f'Examples were not applied: {exc}')
    with st.container(border=True):
        source = st.radio('Signal to test',['Example 1','Example 2','Custom'],horizontal=True,key='region_source_'+id)
        if kind == 'pattern':
            st.caption('Use either applied example, or draw a separate test input.')
            with st.expander('Edit the custom drawing', expanded=False):
                custom = _pattern_editor('region_pixel_'+id,task.prototypes[0])
            gap = 20.
        else:
            st.caption('The two applied sequences can have different orders and lengths. A test can be a separate sequence.')
            custom = st.text_input('Custom sequence · 2–6 symbols from A, B, C','ABBA',key='region_sequence_'+id)
            gap = st.slider('Symbol spacing (ms)',12.,30.,20.,.5,key='region_gap_'+id)
        settings = {}
        variable = lesson['control']
        if variable == 'extra_delay_ms': settings[variable] = st.slider('Additional delay before readout (ms)',0.,60.,0.,5.,key='region_delay_'+id)
        elif variable == 'relay_gain': settings[variable] = st.slider('Input → delayed/convergence transmission',0.,1.5,1.,.1,key='region_relay_'+id)
        elif variable == 'inhibition_gain': settings[variable] = st.slider('Inhibitory transmission gain',0.,2.,1.,.1,key='region_inhibition_'+id)
        elif variable == 'context_nA': settings[variable] = st.slider('Context-cell external input (nA)',0.,.8,.4,.05,key='region_context_'+id)
        elif variable == 'input_nA': settings[variable] = st.slider('Source input current (nA)',.1,1.,.8,.05,key='region_current_'+id)
        st.caption('Inputs use an unseen onset of 12 ms. All displayed times and currents are model protocol settings. '
                   'Editing controls does not calculate or teach until you press a button.')
        run = st.button('Launch the signal', type='primary', width='stretch',key='region_run_'+id)
    try:
        content = task.prototypes[0 if source=='Example 1' else 1] if source!='Custom' else custom if kind=='pattern' else sequence(custom).content
        signal = Signal(kind,content,12.,gap)
        protocol = Protocol(**settings)
    except ValueError as exc:
        if run: st.error(f'Signal was not calculated: {exc}')
        return task,None,None
    if run:
        try:
            result = probe(st.session_state.region_model,signal,protocol,record=True)
            st.session_state['region_record_'+id] = {'after':result, 'before':None, 'task':task, 'captured_presentations':st.session_state.region_model.presentations}
        except (ValueError,FloatingPointError) as exc: st.error(f'Signal was not calculated: {exc}')
    return task,signal,protocol


def _teaching(lesson, task, signal, protocol):
    id = lesson['id']
    with st.expander('Teach these examples · compare with a matched control',expanded=lesson['control']=='teaching'):
        st.write('Teaching presents both applied examples at varied training timings, with an external class label. '
                 'A supervised delta rule changes positive readout strengths between presentations. '
                 'A copy starting with identical weights receives the same input budget with updates disabled.')
        cols = st.columns(2)
        epochs = cols[0].selectbox('Teaching epochs',[32,16,64,8],key='region_epochs_'+id)
        condition = cols[1].selectbox('Update condition',['teaching','disabled','shuffled'],
            format_func=lambda x:{'teaching':'Consistent class teachers','disabled':'Updates disabled','shuffled':'Balanced conflicting teachers'}[x],key='region_condition_'+id)
        st.caption('Each epoch: 16 training signals × 2 presentations. Evaluation: 16 reserved timing variants of the two familiar examples. '
                   'These are counts for a specified task, not intelligence scores or confidence percentages.')
        if st.button('Teach and compare',type='primary',key='region_teach_'+id,disabled=signal is None):
            try:
                model = st.session_state.region_model
                previous = probe(model,signal,protocol,record=True)
                with st.spinner('Calculating source spikes, readout updates and a matched frozen control…'):
                    trained, evidence = controlled_teaching(model,task,epochs=epochs,condition=condition)
                    following = probe(trained,signal,protocol,record=True)
                st.session_state.region_model = trained
                st.session_state['region_evidence_'+id] = evidence
                st.session_state['region_evidence_task_'+id] = task
                st.session_state['region_record_'+id] = {'after':following, 'before':previous, 'task':task, 'captured_presentations':trained.presentations}
                st.success('Teaching complete. The paired recordings below use the exact same query with the before/after weights. Both recordings are frozen probes.')
            except (ValueError,FloatingPointError) as exc: st.error(f'Teaching was not applied: {exc}')
        evidence = st.session_state.get('region_evidence_'+id)
        if evidence:
            if st.session_state.get('region_evidence_task_'+id,task)!=task:
                st.caption('This comparison belongs to the previously taught pair. Teach again to compare the newly applied examples.')
            rows = [{'Weights / condition':label, 'Correct class on reserved timings':f"{evidence[key]['correct']} / {evidence[key]['total']}",
                     'Undecided probes':evidence[key]['abstained']}
                    for key,label in [('before','Before teaching'),('chosen','Chosen update condition'),('disabled','Same-budget disabled control')]]
            st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
            st.caption(f"Recorded comparison · {evidence['update']['condition']} · {evidence['update']['presentations']} presentations per branch · "
                       f"readout parameter change L2 = {evidence['update']['update_l2_nA']:.6f} nA · disabled weights unchanged: {evidence['control_unchanged']}. "
                       'A correct familiar association does not establish transfer to new objects. Other teaching can interfere with earlier associations.')


def _recording(lesson, signal, protocol):
    id = lesson['id']
    saved = st.session_state.get('region_record_'+id)
    result = None
    if saved:
        current_task=st.session_state.region_tasks.get(id,Task.defaults(lesson['kind']))
        if saved.get('task',current_task)!=current_task:
            st.info('The applied example pair has changed. This recording keeps its earlier pair; launch or teach to make a new recording.')
        branch = 'after'
        if saved['before'] is not None:
            branch = st.radio('Inspect the paired query',['after','before'],horizontal=True,
                format_func=lambda x:'After teaching · frozen' if x=='after' else 'Before teaching · frozen', key='region_branch_'+id)
        result = saved[branch]
        if signal != result['signal'] or protocol != result['protocol']:
            st.info('Your next input settings differ from this recording. Launch the signal again to replace it.')
        if result['weight_sha256'] != st.session_state.region_model.fingerprint():
            st.caption('This recording retains its captured weights. The shared model now has different weights; launch again to inspect its current response.')
        comparison=compare_input(result['signal'],saved.get('task',current_task))
        cols = st.columns(4)
        response = 'Undecided' if result['prediction'] is None else 'A-leaning' if result['prediction']==0 else 'B-leaning'
        cols[0].metric('Literal input check',comparison['label'])
        cols[1].metric('Neural class preference',response)
        cols[2].metric('A − B voltage at readout',f"{result['margin_mV']:+.4f} mV")
        cols[3].metric('Cells that emitted a spike',f"{result['active_cells']} / 100")
        if comparison['matchedExample'] is None:
            st.info(comparison['summary']+' The circuit can still lean toward A or B. That preference does not mean an exact match, '
                    'and this two-class readout has no trained unknown-input detector.')
        else:
            st.caption(comparison['summary']+' This literal check is separate from the circuit’s answer; an exact input can still be misclassified.')
        st.caption(f"CAPTURED RECORDING · {len(result['network'].synapses)} links · {result['spike_count']} calculated spikes · "
                   f"readout at {result['readout_ms']:g} ms · weights {result['weight_sha256'][:12]}. "
                   'No weights changed during the query. The playback reveals its neural preference at readout. '
                   'A margin below 0.01 mV abstains; this threshold does not establish that an input is familiar.')
    _view(result,id,task=saved.get('task') if saved else None)
    if result:
        with st.expander('Read the numerical evidence'):
            groups = []
            for _,name,cells,_,detail in GROUPS:
                count = sum(int(cell) in cells for _,cell in result['spikes'])
                groups.append({'Engineering group':name,'Cells':len(cells),'Recorded spikes':count,'Meaning':detail})
            st.dataframe(pd.DataFrame(groups),hide_index=True,width='stretch')
            st.write('Subthreshold voltage carries information even in the readout cells that never emit a spike. '
                     'The anatomy explains biological partners; the table counts only events in the engineered circuit.')
            data = payload(result,id,task=saved.get('task'))
            data.pop('plates') # Event export stays compact; diagrams are distributed in the app.
            if saved.get('task'):
                data['captured_examples']={'kind':saved['task'].kind,'prototypes':saved['task'].prototypes}
            st.download_button('Download this recording and its interpretation',json.dumps(data,allow_nan=False).encode(),
                'synapse_'+id+'_100_neurons.json','application/json',key='region_export_'+id,on_click='ignore')


def _finish(id, key):
    st.session_state.course_notes = {**st.session_state.course_notes,id:st.session_state.get(key,st.session_state.course_notes.get(id,''))}
    progress = st.session_state.course_progress
    st.session_state.course_progress = list(dict.fromkeys(progress+[id]))
    index = next(i for i,l in enumerate(LESSONS) if l['id']==id)
    navigate(LESSONS[index+1]['nav'] if index+1<len(LESSONS) else 'My learning notebook')


def _footer(lesson):
    id = lesson['id']
    key = 'region_reflection_'+id
    with st.expander('Keep a note · optional'):
        st.caption('What changed when you adjusted the experiment?')
        note = st.text_area('My observation',value=st.session_state.course_notes.get(id,''),
                            max_chars=10000,key=key,placeholder='I changed… and noticed…')
        if st.button('Save note',key='region_save_note_'+id):
            st.session_state.course_notes = {**st.session_state.course_notes,id:note}
            st.success('Note saved. You can download it from My learning notebook.')
    index=next(i for i,l in enumerate(LESSONS) if l['id']==id)
    label='Continue to '+LESSONS[index+1]['title']+' →' if index+1<len(LESSONS) else 'Finish in my notebook →'
    st.button(label,type='primary',key='region_continue_'+id,on_click=_finish,args=(id,key))


def _lesson(lesson):
    id = lesson['id']
    notice = st.session_state.pop('region_model_notice',None)
    if notice: st.success(notice)
    st.markdown(f'<div class="eyebrow">SECTION {lesson["number"]} / 12 · HUMAN BRAIN BIOLOGY</div>',unsafe_allow_html=True)
    st.title(lesson['title'])
    from .experience_component import page as activity_page
    activity_page(id)
    with st.expander('Go deeper · cells, circuits and connected regions'):
        activity=ACTIVITIES[id]
        st.markdown('**How this activity connects to biology**')
        st.write(activity['depth'])
        st.caption('What this experiment calculates · '+activity['scope'])
        st.markdown('**Where this happens**');st.write(lesson['sections'][0][1])
        st.markdown('**At the cellular level**');st.write(lesson['cellular'])
        st.markdown('**How the regions coordinate**');st.write(lesson['coordination'])
        st.write(lesson['sections'][1][1])
        st.caption(source_markdown(tuple(dict.fromkeys(activity['sources']+lesson['sources']))))
        st.caption('The halo locates this lesson on a medical illustration. Real tasks recruit interacting networks; '
                   'this app does not measure activity in your brain.')
    movement=id in ('cerebellum','motor')
    from .arena_ui import pause as pause_arena
    if st.toggle('Open the 100-neuron movement microscope' if movement else 'Open the 100-neuron microscope',
            key='region_microscope_'+id,on_change=pause_arena,args=('movement100',)):
        if movement:
            st.caption('Movement → observation → next neural choice. Both movement lessons share this 100-cell controller. '
                       'The earlier 50-cell arena remains in the sidebar.')
            if id=='cerebellum':
                st.info('Follow action, consequence and feedback here; use the reach activity above for an adaptation aftereffect. '
                        'These engineered cells do not simulate Purkinje cells or a cerebellar learning rule.')
            else:
                st.info('The four action populations select a grid move from their voltages. '
                        'Inspect a move to connect a population response with its direction; no muscles are simulated.')
            from .arena_ui import page as arena_page
            arena_page(embedded=True,neurons=100,key_prefix='movement100',lesson_focus=id)
        else:
            st.info(lesson['limits'])
            task,signal,protocol = _input(lesson)
            _teaching(lesson,task,signal,protocol)
            _recording(lesson,signal,protocol)
            with st.expander('Inside the calculation · voltage, groups and synapses'):
                st.latex(r'\tau_m\,\frac{dV}{dt}=E_L-V+R\left(I_{\rm external}+I_{\rm synaptic}\right)')
                st.write('Voltage leaks towards rest; incoming spikes add delayed synaptic currents. '
                         'A threshold crossing emits a spike, resets voltage and starts a refractory interval. '
                         'The two readout groups compare voltages. Teaching changes bounded readout weights; '
                         'a test supplies no teacher and makes no weight updates.')
                st.dataframe(pd.DataFrame([{'Group':name,'Cell IDs':f'N{cells[0]:02}–N{cells[-1]:02}','Cells':len(cells)}
                                          for _,name,cells,_,_ in GROUPS]),hide_index=True,width='stretch')
            _model_controls(id)
    if id == 'hippocampus' and st.toggle('Open the synaptic timing workbench',key='region_synaptic_microscope'):
        with st.container(border=True):
            st.caption('This microscope-scale experiment uses 2 cells and pair-STDP, rather than the 100-cell supervised readout. '
                       'It is embedded here to examine a different level of mechanism; it does not claim to model the hippocampal circuit.')
            from .guided_ui import _experiment, _evidence
            _experiment(embedded=True)
            if 'guided_experiment' in st.session_state: _evidence(embedded=True)
    _footer(lesson)


def _model_controls(id):
    with st.expander('Keep the shared 100-cell model'):
        st.caption(f'{st.session_state.region_model.presentations} teaching presentations · weights {st.session_state.region_model.fingerprint()[:12]}. '
                   'The older 50-cell workbenches retain their own profiles and checkpoint formats.')
        st.download_button('Download 100-cell model',st.session_state.region_model.json_bytes(),
            'synapse_100_cell_model.json','application/json',key='region_model_export_'+id,on_click='ignore')
        upload = st.file_uploader('Restore a 100-cell model · JSON, up to 256 KiB',type=['json'],key='region_model_upload_'+id)
        if st.button('Restore 100-cell weights',disabled=upload is None,key='region_model_restore_'+id):
            try:
                st.session_state.region_model = RegionModel.from_bytes(upload.getvalue())
                st.session_state.region_model_notice = '100-cell weights restored. Existing recordings keep their captured weights.'
                st.rerun()
            except ValueError as exc: st.error(str(exc))
        if st.button('Reset the shared 100-cell weights',key='region_model_reset_'+id):
            st.session_state.region_model = RegionModel()
            st.session_state.region_model_notice = 'Shared weights reset. Existing recordings retain their captured evidence.'
            st.rerun()


def _foundations():
    from . import course_ui as cell
    st.title('Cell foundations')
    st.write('Read a neuron from its inputs to its outputs, then inspect the numerical mechanisms used in every regional lesson.')
    level = st.radio('Explore a mechanism',['Neuron anatomy','Membrane voltage','Chemical synapse','Synaptic plasticity'],horizontal=True,key='region_foundation_level')
    if level == 'Neuron anatomy':
        st.image(asset_uri('neuron_complete.svg'),caption='Complete neuron diagram by Mariana Ruiz Villarreal (LadyofHats), public domain, via Wikimedia Commons. This illustration includes Schwann-cell myelin; CNS myelin is produced by oligodendrocytes.',width='stretch')
        structure = st.selectbox('Follow a structure',['Dendrites','Cell body','Axon initial segment','Axon and myelin','Synaptic terminals'],key='region_cell_structure')
        detail = {
            'Dendrites':'Receive synaptic inputs and integrate them through passive and active membrane properties. Input location and timing matter; our point-neuron model collapses these spatial effects into a single voltage.',
            'Cell body':'Contains the nucleus and supports cellular metabolism and protein production. It also participates electrically; a neuron is a living cell, not only a weighted sum.',
            'Axon initial segment':'A specialised excitable region where many neuronal action potentials initiate. Voltage-gated channel distributions matter. The LIF threshold substitutes a single event rule for those dynamics.',
            'Axon and myelin':'Axons conduct action potentials. Myelin and nodes organise saltatory propagation. Oligodendrocytes form CNS myelin; Schwann cells form PNS myelin. The model uses a specified delay rather than calculating conduction.',
            'Synaptic terminals':'An arriving action potential can open calcium channels, promote vesicle release and influence a receiving cell through receptors. A model spike instead queues a signed current jump.'}
        st.info(detail[structure]);st.caption(source_markdown(['cells','chemical','glia']))
        st.markdown('[Original public-domain illustration and authorship](https://commons.wikimedia.org/wiki/File:Complete_neuron_cell_diagram_en.svg)')
    elif level == 'Membrane voltage':
        st.write('Chemical concentration gradients, selective permeability and electrical forces jointly determine membrane voltage. '
                 'The Na⁺/K⁺ pump maintains gradients; it is not the immediate mechanism of each action-potential downstroke.')
        cell._signals()
    elif level == 'Chemical synapse':
        cell._synapses()
    else: cell._learning()


def _notebook():
    from .course_content import CHAPTERS
    from .course_models import notebook_bytes,notebook_markdown,load_notebook
    st.title('Your learning notebook')
    st.write('Keep your observations and save the experiments you want to return to.')
    from .experience_component import init as init_experiences
    init_experiences()
    with st.expander('Save or restore my experiments'):
        session=st.session_state.experience_session
        st.caption('Keeps the twelve activities, both edited examples, learned values and recognition weights. '
                   'Earlier workbench checkpoints have their own save controls.')
        st.download_button('Download my experiments',session.json_bytes(),
            'synapse_my_experiments.json','application/json',key='experience_bundle_download',on_click='ignore')
        upload_experiments=st.file_uploader('Restore experiments · JSON, up to 2 MiB',type=['json'],key='experience_bundle_upload')
        if st.button('Restore my experiments',disabled=upload_experiments is None,key='experience_bundle_restore'):
            try:
                restored=ExperienceSession.from_bytes(upload_experiments.getvalue())
                restored.epoch=session.epoch+1
                st.session_state.experience_session=restored
                st.session_state.experience_bundle_notice=True
                st.rerun()
            except ValueError as exc: st.error(str(exc))
    if st.session_state.pop('experience_bundle_notice',False): st.success('Your experiments were restored.')
    for c in (*LESSONS,*CHAPTERS):
        if c in CHAPTERS and not st.session_state.course_notes.get(c['id']): continue
        with st.expander(c['number']+' · '+c['title'],expanded=False):
            st.caption('Explored' if c['id'] in st.session_state.course_progress else 'Not marked explored')
            st.write(st.session_state.course_notes.get(c['id']) or 'No reflection saved yet.')
            st.button('Return to section',key='region_note_return_'+c['id'],on_click=navigate,
                      args=(c['nav'] if c in LESSONS else 'Cell foundations',))
    cols = st.columns(2)
    cols[0].download_button('Download readable notebook',notebook_markdown(st.session_state.course_progress,st.session_state.course_notes),
        'synapse_learning_notebook.md','text/markdown',key='course_notebook_md',on_click='ignore',width='stretch')
    cols[1].download_button('Download notebook to restore later',notebook_bytes(st.session_state.course_progress,st.session_state.course_notes),
        'synapse_learning_notebook.json','application/json',key='course_notebook_json',on_click='ignore',width='stretch')
    upload = st.file_uploader('Restore notebook · JSON, up to 256 KiB',type=['json'],key='course_notebook_upload')
    if st.button('Restore learning notebook',disabled=upload is None,key='course_notebook_restore'):
        try:
            progress,notes = load_notebook(upload.getvalue())
            st.session_state.course_progress = progress;st.session_state.course_notes = notes
            st.session_state.region_notebook_restored = True
            st.rerun()
        except ValueError as exc: st.error(str(exc))
    if st.session_state.pop('region_notebook_restored',False): st.success('Notebook restored. Model weights were not changed.')


def page():
    init()
    label = st.session_state.get('course_chapter','Learning journey')
    if label == 'Learning journey': _home()
    elif label == 'Cell foundations': _foundations()
    elif label == 'Glossary':
        from .course_ui import _glossary
        _glossary()
    elif label == 'My learning notebook': _notebook()
    else:
        lesson = next((c for c in LESSONS if c['nav']==label),None)
        if lesson: _lesson(lesson)
        else: navigate('Learning journey');st.rerun()
