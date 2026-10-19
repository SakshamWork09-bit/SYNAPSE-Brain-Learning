"""SYNAPSE local visual laboratory. Launch with: python -m streamlit run streamlit_app.py"""

from dataclasses import asdict, replace
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from synapse import __version__, simulate_network
from synapse.integrated import IntegratedSession, IntegratedConfig, MODES, session_metrics
from synapse.laboratory import Laboratory, MODE_LABELS, run_comparison, comparison_json
from synapse import lab_charts as charts
from synapse.experiments import circuit_experiments
from synapse.learning import (run_seed, model_payload, load_model_payload, neural_prediction)
from synapse.plasticity import PairSTDP, STDPParameters
from synapse.replay import replay_payload, replay_html, probe_payload
from synapse.interventions import ProbeConfig,run_probe,edge_presets,rerun_probe_export

st.set_page_config(page_title='SYNAPSE · Explore the human brain', page_icon='◉', layout='wide',
                   initial_sidebar_state='expanded')
st.markdown('''<style>
[data-testid="stAppViewContainer"] {
 background-color:#fcfaf6;
 background-image:radial-gradient(#d9dfd6 0.7px,transparent 0.7px),radial-gradient(ellipse at 95% 0%,#ffe8d9 0%,transparent 36%);
 background-size:22px 22px,100% 100%;background-attachment:fixed;}
.block-container {padding-top:2rem; padding-bottom:2.5rem; max-width:1250px;}
[data-testid="stSidebar"] {border-right:1px solid #e0ddd4;background:#f3f0e8;}
h1 {letter-spacing:-0.045em; font-weight:700!important;}
h2,h3 {letter-spacing:-0.025em;}
[data-testid="stMetric"] {background:#ffffff; border:1px solid #d4e2df;
 border-radius:12px; padding:14px 18px;}
[data-testid="stMetricValue"] {font-size:1.8rem;}
.eyebrow {font-size:.72rem; letter-spacing:.18em; color:#126d70; margin-bottom:.5rem; font-weight:650;}
.lab-intro {color:#526c75; max-width:850px; line-height:1.6; margin-bottom:1.4rem;}
button {border-radius:14px!important;}
[data-testid="stExpander"] {border-radius:16px;background:#ffffffd9;border-color:#dfdfd6;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:20px!important;}
.st-key-journey_hero {border-radius:28px;background:#ece9fa;padding:clamp(20px,4vw,44px);
 border:1px solid #d7d0ed;position:relative;overflow:hidden;}
.st-key-journey_hero:before {content:'';position:absolute;right:-40px;top:-55px;width:180px;height:180px;
 border:30px solid #f5bc98;border-radius:50%;opacity:.38;pointer-events:none;}
[class*="st-key-route_"] {background:#fffdf8;border:1px solid #dfdbd2!important;border-radius:20px;padding:18px!important;}
.st-key-route_occipital,.st-key-route_parietal,.st-key-route_thalamus {background:#e9f3ee!important;}
.st-key-route_cerebellum,.st-key-route_basal,.st-key-route_hypothalamus {background:#fff0df!important;}
.st-key-route_temporal,.st-key-route_motor,.st-key-route_brainstem {background:#eeebf7!important;}
[class*="st-key-route_"] h3 {font-size:1.15rem;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {font-size:.88rem;}
</style>''', unsafe_allow_html=True)


def stop():
    st.session_state.running = False
    st.session_state.arena_running = False
    st.session_state.movement100_running = False


def advance(count):
    stop()
    try:
        st.session_state.lab.advance(count)
        st.session_state.exports = None
    except (ValueError, FloatingPointError) as exc:
        st.session_state.notice = str(exc)


def start():
    st.session_state.running = st.session_state.lab.remaining > 0


def select_course():
    stop()
    st.session_state.workspace = 'Course'


def title(kicker, heading, description):
    st.markdown(f'<div class="eyebrow">{kicker}</div>', unsafe_allow_html=True)
    st.title(heading)
    st.markdown(f'<div class="lab-intro">{description}</div>', unsafe_allow_html=True)


def plot(fig, key):
    st.plotly_chart(fig, width='stretch', theme=None, key=key,
                    config={'displaylogo':False, 'scrollZoom':False})


if 'lab' not in st.session_state:
    st.session_state.lab = Laboratory()
    st.session_state.running = False
    st.session_state.exports = None
    st.session_state.notice = None

with st.sidebar:
    st.markdown('## ◉ SYNAPSE')
    st.caption('EXPLORE THE HUMAN BRAIN')
    from synapse.region_content import NAV_LABELS,LESSONS
    from synapse.regions_ui import init as init_course
    init_course()
    st.radio('Learning path', NAV_LABELS, key='course_chapter', on_change=select_course)
    explored = sum(c['id'] in st.session_state.course_progress for c in LESSONS)
    st.progress(explored/len(LESSONS),text=f'{explored} of {len(LESSONS)} regions marked explored')
    with st.expander('Advanced controls & earlier workbenches', expanded=False):
        st.caption('Experiments are embedded in the course above. These earlier profiles retain their own controls and checkpoints.')
        page = st.radio('Model workspace', ['Course','Guided lessons','Continuing system','Movement arena','Patterns & sequences','Intervention lab','Structure lab','Learning lab','Guide'],
                        key='workspace', on_change=stop)
    st.divider()
    if page in ('Course','Guided lessons'):
        st.caption('Meet the idea. Try the experiment. Change something and try again.')
    else:
        with st.expander('Create a new session', expanded=False):
            st.caption('Applying these settings replaces the current in-memory session. Download a checkpoint to keep it.')
            with st.form('new_session'):
                seed = st.number_input('Seed', min_value=0, max_value=2**32-1, value=7, step=1,key='new_seed')
                mode = st.selectbox('Feedback condition', MODES, format_func=MODE_LABELS.get,key='new_mode')
                reversal = st.slider('Reverse rule after experience',20,200,100,20,key='new_reversal')
                dt = st.selectbox('Simulation step (ms)',[0.2,0.1],key='new_dt')
                exploration = st.slider('Exploration share',0.0,1.0,0.2,0.05,key='new_exploration')
                if st.form_submit_button('Create new session', width='stretch'):
                    st.session_state.lab = Laboratory(IntegratedSession(int(seed), mode=mode,
                        config=IntegratedConfig(dt_ms=dt, reversal_trial=reversal, exploration=exploration)))
                    stop()
                    st.session_state.exports = None
                    st.session_state.pop('comparison',None)
                    st.session_state.pop('trace_trial',None)
        active = st.session_state.lab.session
        st.caption(f'TWO-CHOICE SESSION · seed {active.seed}\n\n{MODE_LABELS[active.mode]} · {active.config.dt_ms} ms\n\n'
                   f'Rule reversal after {active.config.reversal_trial} experiences')
        with st.expander('Save or restore'):
            st.caption('Download a checkpoint to keep this session after a browser refresh or server restart.')
            if st.button('Prepare downloads', key='prepare_downloads', width='stretch'):
                stop()
                lab = st.session_state.lab
                st.session_state.exports = {'checkpoint':lab.checkpoint(), 'csv':lab.experiences_csv(),
                                             'trial':lab.session.trial_index,'seed':lab.session.seed}
            export = st.session_state.exports
            if export:
                prefix=f"synapse_seed{export['seed']}_experience{export['trial']}"
                st.caption(f"Snapshot after experience {export['trial']}")
                st.download_button('Download checkpoint', export['checkpoint'], prefix+'.json',
                                   'application/json', key='checkpoint_download', on_click='ignore',width='stretch')
                st.download_button('Download experiences CSV', export['csv'], prefix+'.csv',
                                   'text/csv', key='csv_download', on_click='ignore',width='stretch')
            upload=st.file_uploader('Checkpoint JSON · up to 10 MiB',type=['json'],key='checkpoint_upload')
            if st.button('Replace session from file',disabled=upload is None,width='stretch',key='restore_checkpoint'):
                stop()
                try:
                    st.session_state.lab.restore(upload.getvalue())
                    st.session_state.exports=None
                    st.session_state.pop('trace_trial',None)
                    st.session_state.restored=True
                    st.rerun()
                except (ValueError,OverflowError) as exc:
                    st.error(f'Checkpoint was not loaded: {exc}')
    st.divider()
    st.caption(f'v{__version__} · CPU simulation\n\nCreated by Saksham Singh Chowhan')

if st.session_state.pop('restored',False):
    st.success('Session restored. Advance to record a new activity window.')
if st.session_state.notice:
    st.error(st.session_state.notice)
    st.session_state.notice = None


def continuing_page():
    title('CONTINUING SYSTEM / 50 NEURONS', 'Signals. Choices. Consequences.',
          'A two-cue, two-button experiment you can follow. Watch the input, actual neural activity, '
          'the chosen action and the feedback that changes connections. Movement arena is a separate workspace.')
    view=st.radio('Activity view',['Observe experience','Charts and details'],horizontal=True,
                   key='activity_view',on_change=stop)
    lab=st.session_state.lab
    cols=st.columns([1,1,1.2,1.6,2])
    cols[0].button('Start',on_click=start,disabled=st.session_state.running or lab.remaining==0,
                   type='primary',width='stretch',key='start')
    cols[1].button('Pause',on_click=stop,disabled=not st.session_state.running,width='stretch',key='pause')
    cols[2].button('Step 1',on_click=advance,args=(1,),disabled=lab.remaining==0,width='stretch',key='step_one')
    cols[3].button('Advance 20',on_click=advance,args=(20,),disabled=lab.remaining==0,width='stretch',key='step_twenty')
    cols[4].caption('Start calculates one experience every 8 seconds in Observe view; 0.8 seconds in Charts view. '
                    'Pause the session to inspect slow replays.')

    @st.fragment(run_every=(8.0 if view=='Observe experience' else 0.8) if st.session_state.running else None)
    def workspace():
        lab=st.session_state.lab
        if st.session_state.running:
            try:
                lab.advance(1)
                st.session_state.exports=None
            except (ValueError,FloatingPointError) as exc:
                stop()
                st.session_state.notice=str(exc)
                st.rerun()
            if not lab.remaining:
                stop()
                st.rerun()
        s=lab.session
        records=s.records
        if view=='Observe experience':
            window=None
            if lab.windows:
                options=[w.trial for w in lab.windows]
                cols=st.columns([1,2])
                follow=cols[0].toggle('Follow newest recording',value=True,key='observe_follow',
                                      disabled=st.session_state.running)
                if follow or st.session_state.get('observe_trial') not in options:
                    st.session_state.observe_trial=options[-1]
                trial=cols[1].selectbox('Experience to replay',options,
                    format_func=lambda n:f'Experience {n+1}',key='observe_trial',
                    disabled=follow or st.session_state.running)
                window=next(w for w in lab.windows if w.trial==trial)
            payload=replay_payload(s,window)
            html=replay_html(payload)
            # Browser frames replay an immutable recording. They never call the engine.
            st.iframe(html,height='content',tab_index=0,
                       alt='Recorded neural input, action, feedback and automatic network animation')
            if window is not None:
                st.download_button('Download this interactive replay (.html)',html,
                    f'synapse_experience_{window.trial+1}_replay.html','text/html',
                    key='replay_download',on_click='ignore')
            st.caption('This display replays calculated events. Start / Step above creates new experiences; '
                       'Play / Pause inside the display only controls playback. No movement or navigation is claimed yet.')
        cols=st.columns(4)
        cols[0].metric('Experiences',f'{s.trial_index:,}',help='Maximum 1,000 per continuing session.')
        recent=records[-20:]
        cols[1].metric('Recent success',f"{100*np.mean([r['reward'] for r in recent]):.0f}%" if recent else '—',
                       help='Actual rewards over up to 20 most recent experiences. Online learning stays active.')
        cols[2].metric('Neurons active so far',f'{np.count_nonzero(s.engine.total_spikes)} / 50')
        cols[3].metric('Simulation time',f'{s.engine.time_ms/1000:.1f} s')
        phase='A → 0, B → 1' if s.trial_index<s.config.reversal_trial else 'A → 1, B → 0'
        status='Running' if st.session_state.running else 'Paused'
        st.caption(f'{status} · {MODE_LABELS[s.mode]} · current environment rule: {phase}. '
                   'The circuit receives outcome feedback after its action; this display reveals the rule to you.')
        if s.trial_index==s.config.session_limit:
            st.info('Session budget reached. Download this session or create a new one.')
        if view=='Observe experience':
            if not records:
                st.info('Press Step 1. You will see a signal, an action at 25 ms, then feedback and connection changes at 35 ms.')
            return
        if records:
            left,right=st.columns(2)
            with left:plot(charts.success_chart(records,s.config.reversal_trial),'live_success')
            with right:plot(charts.preference_chart(records,s.config.reversal_trial),'live_preferences')
            latest=records[-1]
            st.caption(f"Latest · experience {latest['trial']+1}: cue {'AB'[latest['cue']]} → action {latest['action']}"
                       f" · actual reward {latest['reward']} · delivered feedback {latest['delivered_feedback']:.0f}")
        else:
            st.info('Press Step 1 to calculate your first experience, or Start to advance automatically.')
        st.subheader('Inside the circuit')
        st.caption('50 cells · 690 directed connections · 200 adaptive association-to-action connections. '
                   'A trace is a recorded experience; inspecting it does not rerun its physics.')
        cols=st.columns([1,2])
        neuron=cols[0].selectbox('Inspect neuron',list(range(50)),index=40,format_func=lambda n:f'N{n}',key='inspect_neuron')
        window=None
        if lab.windows:
            options=[w.trial for w in lab.windows]
            follow=cols[1].toggle('Follow latest experience',value=True,key='follow_latest')
            if follow or st.session_state.get('trace_trial') not in options:
                st.session_state.trace_trial=options[-1]
            trial=cols[1].selectbox('Recorded experience',options,format_func=lambda n:f'Experience {n+1}',key='trace_trial',disabled=follow)
            window=next(w for w in lab.windows if w.trial==trial)
            elapsed=st.slider('Playback cursor within this experience (ms)',0,100,25,1,key='playback_cursor')
            cursor=window.time_ms[0]+elapsed
            index=min(np.searchsorted(window.time_ms,cursor),len(window.time_ms)-1)
            flash=np.unique(window.spike_neurons[np.abs(window.spike_times_ms-cursor)<=0.5])
            counts=np.bincount(window.spike_neurons,minlength=50)
            voltage=window.voltage_mV[index]
            st.caption('The cursor scrubs calculated samples. White flashes mark recorded spikes within 0.5 ms; '
                       'node sizes count spikes across this whole experience. Connections below show current weights.')
        else:
            cursor=None;flash=();counts=s.engine.total_spikes;voltage=s.engine.voltage
            st.caption('Current boundary voltages and cumulative spike counts. Dense playback becomes available after an advance.')
        left,right=st.columns([1.1,1])
        with left:
            plot(charts.network_view(s.engine.network,s.engine.weights,selected=neuron,voltage=voltage,
                                     spike_counts=counts,flash=flash),'live_network')
            st.caption('Incident connections of the selected neuron are shown. Teal = positive; orange = inhibitory. '
                       'Hover cells for values; direction and strength appear in the connection table.')
        with right:
            if window is not None:
                plot(charts.voltage_chart(window.time_ms,window.voltage_mV,neuron,
                    threshold=s.engine.network.neuron.threshold_mV,current_times=window.current_time_ms,
                    current=window.synaptic_current_nA,cursor=cursor),'live_voltage')
            else:
                plot(charts.weight_matrix(s.engine.network,s.engine.weights,eligible=True),'initial_weights')
                st.caption('Initial adaptive strengths. Source N10–29 → receiving N40–49.')
        if window is not None:
            plot(charts.raster(window.spike_times_ms,window.spike_neurons,start=window.time_ms[0],
                               stop=window.time_ms[-1],cursor=cursor),'live_raster')
            st.download_button('Download this experience trace (.npz)',lab.trace_bytes(window.trial),
                               f'experience_{window.trial+1}_trace.npz','application/octet-stream',
                               key='trace_download',on_click='ignore')
        with st.expander('Current weights and connection details'):
            plot(charts.weight_matrix(s.engine.network,s.engine.weights,eligible=True),'adaptive_weights')
            selected=set(s.engine.selected)
            rows=[{'source':e.source,'target':e.target,'strength_nA':float(w),'delay_ms':e.delay_ms,
                   'adaptive':i in selected} for i,(e,w) in enumerate(zip(s.engine.network.synapses,s.engine.weights))
                   if neuron in (e.source,e.target)]
            st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        with st.expander('Experience history'):
            st.dataframe(pd.DataFrame([{'experience':r['trial']+1,'cue':'AB'[r['cue']],
                                       'action':r['action'],'actual reward':r['reward'],
                                       'delivered feedback':r['delivered_feedback']} for r in records]),
                         hide_index=True,width='stretch')
    workspace()

    st.divider()
    st.subheader('Compare outcome feedback with controls')
    st.caption('Runs three independent sessions with the same selected seed, initial wiring and cue sequence. '
               'Your current continuing session is preserved. One seed is exploratory evidence.')
    supported_reversal=st.session_state.lab.session.config.reversal_trial<=380
    if not supported_reversal:
        st.info('This imported session reverses too late for a 400-experience comparison. Create a session with an earlier reversal to compare controls.')
    if st.button('Run matched comparison',disabled=st.session_state.running or not supported_reversal,key='compare'):
        s=st.session_state.lab.session
        total=min(400,max(200,s.config.reversal_trial+100))
        with st.spinner(f'Calculating three {total}-experience sessions…'):
            result=run_comparison(s.seed,replace(s.config,session_limit=1000),total)
            st.session_state.comparison={'results':result,'seed':s.seed,'reversal':s.config.reversal_trial,
                                          'config':asdict(s.config),'total':total}
    if 'comparison' in st.session_state:
        c=st.session_state.comparison
        st.caption(f"Saved comparison · seed {c['seed']} · {c['total']} experiences per condition · "
                   f"reversal after {c['reversal']} · {c['config']['dt_ms']} ms step · exploration {c['config']['exploration']:.0%}")
        plot(charts.comparison_chart(c['results'],c['reversal']),'comparison_chart')
        rows=[]
        for mode,records in c['results'].items():
            m=session_metrics(records,c['reversal'])
            rows.append({'condition':MODE_LABELS[mode],'before reversal':f"{m['before_reversal_accuracy']:.1%}",
                         'first 20 after':f"{m['after_reversal_accuracy']:.1%}",'final 20':f"{m['final_window_accuracy']:.1%}"})
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        st.download_button('Download comparison JSON',comparison_json(c['results'],c['seed'],c['reversal']),
                           'synapse_comparison.json','application/json',on_click='ignore')


def intervention_page():
    title('INTERVENTION LAB / FROZEN CIRCUIT PROBES','Change a cause. Watch the effect.',
          'Inject a pulse, block a pathway or scale inhibition. Two copies begin from the same neural state. '
          'Their responses are calculated with learning frozen; your continuing session stays intact.')
    s=st.session_state.lab.session
    kind=st.radio('Experiment type',['connections','stimulus'],horizontal=True,key='probe_kind',
                  format_func=lambda k:'Connection controls · same pulse in both copies' if k=='connections'
                  else 'Stimulus effect · pulse versus no added input')
    groups={'Sensory A (N0–4)':tuple(range(5)),'Sensory B (N5–9)':tuple(range(5,10)),
            'Association A (N10–19)':tuple(range(10,20)),'Association B (N20–29)':tuple(range(20,30)),
            'Inhibitory A (N30–34)':tuple(range(30,35)),'Inhibitory B (N35–39)':tuple(range(35,40)),
            'Action 0 (N40–44)':tuple(range(40,45)),'Action 1 (N45–49)':tuple(range(45,50))}
    stim_group=st.selectbox('Stimulate',list(groups)+['Custom neurons'],key='probe_group')
    if stim_group=='Custom neurons':
        selected_neurons=st.multiselect('Choose one to twenty neurons',range(50),default=[0],max_selections=20,key='probe_neurons')
    else:selected_neurons=groups[stim_group]
    presets=edge_presets(s.engine.network)
    if kind=='connections':
        edge_mode=st.selectbox('Connections to control',['Pathway preset','Single connection','Custom connections'],key='probe_edge_mode')
        if edge_mode=='Pathway preset':
            pathway=st.selectbox('Pathway',list(presets),key='probe_pathway')
            selected_edges=presets[pathway]
        else:
            edge_format=lambda i:f'N{s.engine.network.synapses[i].source} → N{s.engine.network.synapses[i].target} · {s.engine.weights[i]:+.4f} nA'
            if edge_mode=='Single connection':
                selected_edges=(st.selectbox('Connection',range(len(s.engine.weights)),format_func=edge_format,key='probe_edge'),)
            else:
                selected_edges=tuple(st.multiselect('Choose connections',range(len(s.engine.weights)),max_selections=50,
                                                     format_func=edge_format,key='probe_edges'))
        st.caption(f'{len(selected_edges)} selected connections. A gain of 0 blocks them; 1 restores normal transmission; '
                   '2 doubles transmitted current. Existing synaptic current is not erased.')
    else:selected_edges=()
    with st.form('probe_settings'):
        left,right=st.columns(2)
        with left:
            amplitude=st.slider('Pulse amplitude (nA)',-1.0,1.0,.8,.05,key='probe_amplitude')
            start_ms=st.slider('Pulse begins (ms)',0,80,5,1,key='probe_start')
            width_ms=st.slider('Pulse width (ms)',1,20,5,1,key='probe_width')
        with right:
            duration=st.selectbox('Probe duration (ms)',[100,200],key='probe_duration')
            initial_state=st.selectbox('Starting state',['current','resting'],key='probe_initial',
                format_func=lambda k:'Current session state, including queued signals' if k=='current'
                else 'Resting copy, keeping current learned weights')
            gain=st.slider('Selected connection gain',0.0,2.0,0.0,.1,key='probe_gain',disabled=kind!='connections')
            inhibition=st.slider('All inhibitory connection gain',0.0,2.0,1.0,.1,key='probe_inhibition',disabled=kind!='connections')
        st.caption('These are temporary transmission controls, not edits to learned weights. Overlapping gains multiply. '
                   'No teaching, action decoder or reward update runs during a probe.')
        submitted=st.form_submit_button('Run paired probe',type='primary',width='stretch')
    if submitted:
        stop()
        try:
            cfg=ProbeConfig(kind=kind,neurons=tuple(selected_neurons),amplitude_nA=amplitude,
                            pulse_start_ms=float(start_ms),pulse_width_ms=float(width_ms),duration_ms=float(duration),
                            edges=tuple(selected_edges),edge_gain=gain if kind=='connections' else 1.0,
                            inhibitory_gain=inhibition if kind=='connections' else 1.0,initial_state=initial_state)
            result=run_probe(s.engine,cfg)
            st.session_state.probe_result=result
            st.session_state.probe_context={'seed':s.seed,'completed_experiences':s.trial_index,'mode':s.mode}
            st.session_state.pop('probe_inspect',None)
        except (ValueError,FloatingPointError) as exc:st.error(f'Probe was not run: {exc}')
    with st.expander('Reproduce an exported probe'):
        imported=st.file_uploader('Experiment JSON (not a session checkpoint)',type=['json'],key='probe_upload')
        if st.button('Run exported experiment',disabled=imported is None,key='probe_import'):
            try:
                candidate=rerun_probe_export(imported.getvalue())
                if candidate.initial_engine_state['network']['n_neurons']!=50:
                    raise ValueError('this interface requires the 50-neuron profile')
                st.session_state.probe_result=candidate
                # Provenance labels are display-only; model state comes from validated JSON.
                context=json.loads(imported.getvalue()).get('source_context',{})
                st.session_state.probe_context=context if isinstance(context,dict) else {}
                st.session_state.pop('probe_inspect',None)
            except (ValueError,FloatingPointError) as exc:st.error(f'Experiment was not loaded: {exc}')
    if 'probe_result' not in st.session_state:
        st.info('Try the defaults: pulse Sensory A, block Sensory A → association A, then Run paired probe. '
                'Compare the response with identical input and no blocked connections.')
        return
    result=st.session_state.probe_result;context=st.session_state.probe_context;cfg=result.configuration
    summary=result.summary()
    st.divider()
    st.subheader('Recorded comparison')
    st.caption(f"Source snapshot {result.source_sha256[:12]} · neural time {result.source_time_ms:.1f} ms · "
               f"{cfg.initial_state} initial dynamics · {cfg.kind} experiment. Settings above apply only when you run again.")
    st.write(f"**Recorded pulse:** {cfg.amplitude_nA:+.2f} nA to "+', '.join(f'N{i}' for i in cfg.neurons)+
             f' from {cfg.pulse_start_ms:g} to {cfg.pulse_start_ms+cfg.pulse_width_ms:g} ms. '
             f'**Manual gains:** selected {cfg.edge_gain:g}×; inhibition {cfg.inhibitory_gain:g}×.')
    st.caption('Control has the same pulse and normal transmissions.' if cfg.kind=='connections'
               else 'Control receives no added pulse; intervention receives the recorded pulse. Connections are identical.')
    cols=st.columns(5)
    cols[0].metric('Control spikes',summary['branches']['control']['spikes'])
    cols[1].metric('Intervention spikes',summary['branches']['intervention']['spikes'])
    cols[2].metric('Blocked connections',summary['branches']['intervention']['blocked_connections'])
    cols[3].metric('Largest voltage effect',f"{summary['maximum_voltage_difference_mV']:.2f} mV")
    cols[4].metric('Learned weight changes','0',help='Neither branch receives outcome feedback or weight updates.')
    branch=st.radio('Replay branch',['intervention','control'],horizontal=True,key='probe_branch')
    payload=probe_payload(result,branch,seed=context.get('seed'))
    html=replay_html(payload)
    st.iframe(html,height='content',tab_index=0,alt='Frozen intervention recording with manual pulse and connection controls')
    st.caption('Grey dashed links are blocked. Amber links have a manual gain. Play and scrub inspect this recorded branch. '
               'The continuing system has not advanced or changed.')
    default_neuron=cfg.neurons[0] if cfg.kind=='stimulus' else result.initial_engine_state['network']['synapses'][cfg.edges[0]]['target'] if cfg.edges else 10
    neuron=st.selectbox('Compare neuron voltage',range(50),index=default_neuron,key='probe_inspect',format_func=lambda n:f'N{n}')
    fig=go.Figure()
    for b,color in ((result.control,charts.CYAN),(result.intervention,charts.ORANGE)):
        fig.add_trace(go.Scatter(x=b.window.time_ms-b.window.time_ms[0],y=b.window.voltage_mV[:,neuron],
                                name=b.name,mode='lines',line=dict(color=color,width=2)))
    fig.add_hline(y=result.initial_engine_state['network']['neuron']['threshold_mV'],line_dash='dot',line_color='#74828d')
    plot(charts.finish(fig,height=320,x='Time since probe start (ms)',y=f'N{neuron} voltage (mV)'),'probe_voltage')
    with st.expander('Per-neuron response and intervention details'):
        rows=[{'neuron':i,'control spikes':int(result.control.spike_counts[i]),
               'intervention spikes':int(result.intervention.spike_counts[i]),
               'control peak mV':float(result.control.window.voltage_mV[:,i].max()),
               'intervention peak mV':float(result.intervention.window.voltage_mV[:,i].max())} for i in range(50)]
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        st.json({'configuration':asdict(cfg),'maximum_voltage_difference_mV':summary['maximum_voltage_difference_mV'],
                 'maximum_synaptic_current_difference_nA':summary['maximum_synaptic_current_difference_nA']})
    cols=st.columns(4)
    cols[0].download_button('Experiment JSON',result.json_bytes(context),'synapse_probe.json','application/json',on_click='ignore')
    cols[1].download_button('Both traces (.npz)',result.npz_bytes(),'synapse_probe_traces.npz','application/octet-stream',on_click='ignore')
    cols[2].download_button('Neuron table CSV',result.neuron_csv(),'synapse_probe_neurons.csv','text/csv',on_click='ignore')
    cols[3].download_button('Replay HTML',html,f'synapse_probe_{branch}.html','text/html',on_click='ignore')
    st.caption('To restore normal transmission, set both gains to 1 and run again from the same source state. '
               'This tests reversibility of a manual intervention; it does not demonstrate biological repair or relearning.')


def structure_page():
    title('STRUCTURE LAB / 12 NEURONS','Follow a signal.',
          'Compare propagation, branching, inhibition and feedback in controlled circuits. '
          'Each run begins from rest; these experiments are separate from your continuing session.')
    protocols=circuit_experiments()
    index=st.selectbox('Circuit experiment',range(len(protocols)),format_func=lambda i:protocols[i].title,key='circuit_choice')
    experiment=protocols[index]
    st.write(experiment.description)
    if st.button('Run circuit',type='primary',key='run_circuit'):
        result=simulate_network(experiment.network,duration_ms=experiment.duration_ms,dt_ms=.1,
                                external_current_nA=experiment.input_nA)
        st.session_state.circuit=(experiment,result)
    if 'circuit' not in st.session_state:
        st.info('Select a circuit and run it to see the computed signal path.')
        return
    experiment,result=st.session_state.circuit
    st.caption(f'DISPLAYED RUN · {experiment.title} · 200 ms · 0.1 ms step')
    cols=st.columns(3)
    cols[0].metric('Spikes',len(result.spike_times_ms))
    cols[1].metric('Active neurons',np.count_nonzero(result.spike_counts))
    cols[2].metric('Connections',len(experiment.network.synapses))
    neuron=st.selectbox('Inspect circuit neuron',range(12),index=5,key='circuit_neuron')
    left,right=st.columns(2)
    weights=np.array([s.weight_nA for s in experiment.network.synapses])
    with left:
        plot(charts.network_view(experiment.network,weights,selected=neuron,
                                 voltage=result.voltage_mV[-1],spike_counts=result.spike_counts),'circuit_network')
        st.caption('Selected cell’s incident connections. Node sizes show whole-run spike counts; hover shows final voltage.')
    with right:
        plot(charts.voltage_chart(result.time_ms,result.voltage_mV,neuron,
                                 threshold=experiment.network.neuron.threshold_mV,
                                 current_times=result.time_ms[:-1],current=result.synaptic_current_nA),'circuit_voltage')
    plot(charts.raster(result.spike_times_ms,result.spike_neurons,start=0,stop=200,n=12),'circuit_raster')
    with st.expander('Connections and input recipe'):
        st.dataframe(pd.DataFrame([asdict(s) for s in experiment.network.synapses]),hide_index=True,width='stretch')
        st.json(list(experiment.stimulus_recipe))
    st.caption('Try Signal propagation, then One connection removed. The source input stays the same; downstream activity changes.')


def learning_page():
    title('LEARNING LAB / CONTROLLED EXPERIMENTS','See what changes a connection.',
          'Explore local spike timing, then a supervised temporal-order task. '
          'These use separate experimental circuits and leave the continuing system intact.')
    pair_tab,task_tab=st.tabs(['Spike timing','Temporal-order learning'])
    with pair_tab:
        st.subheader('Which spike arrives first?')
        lag=st.slider('Post-spike time minus pre-arrival time (ms)',-60,60,10,1,key='pair_lag')
        def pair_change(lag):
            rule=PairSTDP([.1],STDPParameters())
            if lag>0:rule.events(100,pre_arrivals=(0,));rule.events(100+lag,post_spikes=(0,))
            elif lag<0:rule.events(100+lag,post_spikes=(0,));rule.events(100,pre_arrivals=(0,))
            else:rule.events(100,pre_arrivals=(0,),post_spikes=(0,))
            return float(rule.weights_nA[0]-.1)
        lags=np.arange(-60,61)
        delta=pair_change(lag)
        cols=st.columns(3)
        cols[0].metric('Before','0.10000 nA')
        cols[1].metric('After',f'{.1+delta:.5f} nA')
        cols[2].metric('Change',f'{delta:+.5f} nA')
        fig=go.Figure(go.Scatter(x=lags,y=[pair_change(int(v)) for v in lags],
                                mode='lines',line=dict(color=charts.CYAN),name='Calculated pair update'))
        fig.add_trace(go.Scatter(x=[lag],y=[delta],mode='markers',marker=dict(color=charts.ORANGE,size=12),name='Your timing'))
        plot(charts.finish(fig,x='Post spike − local pre-arrival time (ms)',y='Weight change (nA)'),'pair_window')
        st.caption('Positive lag strengthens this connection; negative lag weakens it; a new simultaneous pair has zero change. '
                   'This is the specified PairSTDP rule. The continuing system adds a separate reward-gated eligibility mechanism.')
    with task_tab:
        seed=st.number_input('Temporal task seed',min_value=0,max_value=2**32-1,value=11,step=1,key='temporal_seed')
        st.caption('32 teaching examples, 24 disjoint test timings, four neural conditions and a last-event heuristic. '
                   'Test inference starts from rest with frozen weights and no teaching current.')
        if st.button('Run temporal learning',key='run_temporal',type='primary'):
            with st.spinner('Training and evaluating independent conditions…'):
                st.session_state.temporal=run_seed(int(seed))
        if 'temporal' in st.session_state:
            result=st.session_state.temporal
            st.caption(f"DISPLAYED RUN · seed {result['seed']} · 24 held-out test examples")
            labels={'before':'Before training','trained':'Correct teaching','learning_disabled':'Learning disabled',
                    'shuffled_teachers':'Shuffled teaching'}
            rows=[{'condition':labels[k],'test accuracy':f"{v['metrics']['accuracy']:.1%}"}
                  for k,v in result['conditions'].items()]
            rows.append({'condition':'Last-event heuristic','test accuracy':f"{result['last_event_heuristic']['accuracy']:.1%}"})
            st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
            st.caption('This toy distribution can be solved by recency. Compare the simple heuristic too; '
                       'success here does not establish general sequence learning.')
            st.subheader('Query the frozen trained circuit')
            cols=st.columns(2)
            a=cols[0].slider('A pulse time (ms)',10,75,25,1,key='query_a')
            b=cols[1].slider('B pulse time (ms)',10,75,55,1,key='query_b')
            network,config=load_model_payload(model_payload(result))
            try:
                prediction,trace=neural_prediction(network,(a,a,b,b),config)
                st.success('Circuit predicts: '+('A then B' if prediction['prediction']==0 else 'B then A'))
                cols=st.columns(2)
                cols[0].metric('AB output above rest',f"{prediction['score_AB_mV']:.4f} mV")
                cols[1].metric('BA output above rest',f"{prediction['score_BA_mV']:.4f} mV")
                fig=go.Figure()
                for n,color,label in ((4,charts.CYAN,'AB output'),(5,charts.LILAC,'BA output')):
                    fig.add_trace(go.Scatter(x=trace.time_ms,y=trace.voltage_mV[:,n],name=label,
                                            mode='lines',line=dict(color=color)))
                fig.add_vline(x=90,line_dash='dash',line_color=charts.ORANGE)
                plot(charts.finish(fig,x='Time (ms)',y='Output voltage (mV)'),'temporal_query')
            except ValueError as exc:
                st.info(f'Choose separated A and B timings: {exc}')
            st.download_button('Download trained temporal model',json.dumps(model_payload(result),indent=2),
                               'temporal_model.json','application/json',on_click='ignore')


def guide_page():
    title('FIELD GUIDE','An experiment you can inspect.',
          'SYNAPSE calculates simplified spiking neurons and their interactions. '
          'It is an engineered neural laboratory with explicit inputs, action decoding and learning rules.')
    st.markdown('''
**Begin with the Learning path.** The main app follows six neuroscience chapters:
brain and cells, electrical signals, synapses, branching networks, learning and
memory, then brain and behaviour. Explore the illustrations, run the model
experiments inside each chapter, and save reflections in My learning notebook.
The home page's Launch a signal uses the familiar branching recording. These
model roles are separate from the anatomical brain illustrations.

**Use further exploration when useful.** This optional model-tools section keeps
the older workbenches and checkpoints. The earlier standalone timing lesson is
also available there; the same experiment is embedded in Learning and memory.

**Explore the continuing system.** Open Continuing system, then Observe experience.
Press **Step 1** and watch the input, travelling
signals, action and later feedback. All 50 neurons and 690 connections appear
automatically. Click a neuron only when you want extra detail. Play/Pause inside
the view controls a recording; Start/Pause above it controls new simulation.

**Give the controller a world.** Movement arena has a separate 50-cell profile
with four actions. Run frozen evaluation before training, press Train 20 episodes
five times, then evaluate again. Compare current weights, reset weights, random
movement and simple greedy sensors on identical reserved journey starts. Turn on
Frozen greedy play and Start moving to watch what it learned without updates or
exploration. Edit walls/hazards to make a new arena, or evaluate the edited map
with existing weights. The open board is a small sensor-guided task; detour
planning is limited. Arena checkpoint controls are inside that workspace.

**Then inspect learning over experiences.** Advance 20 five times to reach the
default reversal, then another 100 experiences. Charts and details shows recent
success and four mean connection-strength curves. Start advances one experience
about every eight seconds in Observe view, or 0.8 seconds in Charts view.

**Inspect a recorded experience.** Move the replay cursor or use Charts and details
for a selected neuron's voltage/current trace and the spike raster.
Only the last eight dense experience traces are retained. All outcome and weight
preference history remains available, up to the 1,000-experience session budget.
Current weights are distinct from historical voltage playback.

**Change the circuit's conditions.** Open Intervention lab and run the default
paired probe. Both copies receive the same pulse; one blocks Sensory A's links
to its association group. Compare the animation, voltage overlay and spike counts.
Set connection gain to 1 and rerun to reproduce the control response. Stimulus
effect instead compares a pulse with no added input. Try a negative pulse to
see hyperpolarization. The live session stays unchanged, and probe learning is
frozen. Download experiment JSON to reproduce the exact source and settings.
These are temporary transmission controls, not new wiring or adaptive recovery.

**Keep your session.** Open Save or restore, prepare downloads, and download the
checkpoint. Browser refreshes or server restarts can clear in-memory sessions.
Restore a downloaded checkpoint to retain neural state, delayed signals, learning
traces, connections, environment history and future random choices. Dense playback
windows are not in checkpoints; advance once after restore to record another.

**Test learning against controls.** Pause and run the matched comparison. Its three
sessions share initial wiring and cues for the selected seed, but remain independent.
The uncorrelated-feedback condition uses independent random feedback. Learning
continues during evaluation, so these percentages are online success, not held-out
accuracy. A single seed and short windows provide limited evidence.

**Explore earlier experiments.** Structure lab has six controlled 12-neuron circuits.
Learning lab includes pair STDP and the six-neuron supervised temporal-order task.
These separate circuits leave your continuing session unchanged. Temporal task
accuracy is measured on disjoint test timings with frozen inference.

**Read the model.** The supplied docs/INTEGRATED_SYSTEM.md defines the 50-cell
controller and its limits. docs/INTERFACE.md explains controls, data and exports.
All experiments run on the CPU. The local app needs no API key or paid service.
''')


if page=='Course':
    from synapse.course_ui import page as course_page
    course_page()
elif page=='Guided lessons':
    from synapse.guided_ui import page as guided_page
    guided_page()
elif page=='Continuing system':continuing_page()
elif page=='Intervention lab':intervention_page()
elif page=='Movement arena':
    from synapse.arena_ui import page as arena_page
    arena_page()
elif page=='Patterns & sequences':
    from synapse.memory_ui import page as memory_page
    memory_page()
elif page=='Structure lab':structure_page()
elif page=='Learning lab':learning_page()
else:guide_page()
