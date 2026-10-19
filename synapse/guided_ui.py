"""A beginner path around a controlled, measured plasticity experiment."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from .guided_timing import (CONDITIONS, INITIAL_WEIGHT_NA, RULE, TimingConfig,
                            run_experiment, explanation, notebook)
from .guided_view import biology_html, replay_html, replay_payload
from . import lab_charts as charts

STEPS = ['1 · Meet the idea', '2 · Run the experiment', '3 · Explain the evidence']
PREDICTIONS = ['I am unsure', 'It will strengthen', 'It will weaken', 'It will stay unchanged']
_editor = components.declare_component('synapse_timing_editor',
    path=str(Path(__file__).resolve().parents[1] / 'ui_assets' / 'timing_editor'))


def _go(step):
    st.session_state.guided_started = True
    st.session_state.guided_step = STEPS[step]


def _home():
    st.session_state.guided_started = False


def _timing_changed():
    st.session_state.guided_revision = st.session_state.get('guided_revision', 0) + 1


def _preset(lag):
    st.session_state.guided_lag = lag
    _timing_changed()


def accept_editor(value, revision):
    """Validate a browser proposal; stale renders cannot overwrite newer settings."""
    return (isinstance(value, dict) and type(value.get('revision')) is int
            and value['revision'] == revision and type(value.get('lag_ms')) is int
            and -40 <= value['lag_ms'] <= 40 and type(value.get('sequence')) is int
            and value['sequence'] > 0)


def _plot(fig, key):
    st.plotly_chart(fig, width='stretch', theme=None, key=key,
                    config={'displaylogo': False, 'scrollZoom': False})


def _landing():
    st.markdown('### Explore how learning can happen')
    st.write('Start with a question, change one condition, and follow the evidence. '
             'Each guided experiment explains its model and its connection to biology.')
    with st.container(border=True):
        st.caption('LESSON 01 · AVAILABLE NOW · TWO NEURONS, ONE CONNECTION')
        st.subheader('Can timing change a connection?')
        st.write('The same two neurons. A different order. Predict what happens, '
                 'then compare their measured connection strengths.')
        st.button('Start the timing lesson', type='primary', key='guided_start',
                  on_click=_go, args=(0,))
        if 'guided_experiment' in st.session_state:
            st.button('Return to my last result', key='guided_resume', on_click=_go, args=(2,))
    with st.expander('Where this learning journey goes next'):
        st.write('Planned lessons: signals and thresholds; excitation and inhibition; '
                 'learning from feedback; recognition of unseen examples; interference and rehearsal.')
        st.caption('These guided lessons are planned. The existing advanced workspaces remain available in the sidebar.')
    st.info('A small model can help explain a principle. Each lesson tells you which parts are '
            'calculated, which are illustrated, and what the comparison can establish.')


def _meet():
    st.subheader('First, meet the connection')
    st.write('Think about learning a new button combination: order can matter. '
             'Our question here is narrower: does the relative timing of two neural events '
             'change a connection under a particular learning rule?')
    st.iframe(biology_html(), height='content', alt='Interactive biology illustration of a chemical synapse')
    st.caption('Biology background: [NCBI MeSH · synaptic transmission](https://www.ncbi.nlm.nih.gov/mesh/68009435). '
               'The animation introduces communication; it does not depict the molecular mechanism of plasticity.')
    with st.container(border=True):
        st.markdown('**In our experiment**')
        st.write('A is the sending neuron. B is the receiving neuron. We use brief external pulses '
                 'to make each fire once, and change when B fires relative to A’s signal arriving. '
                 'We then measure the connection’s strength.')
        st.caption('The two spikes are deliberately evoked during training. A later source-only test '
                   'checks transmission without directly stimulating B.')
    st.button('Try the experiment →', type='primary', key='guided_try', on_click=_go, args=(1,))


def _experiment(embedded=False):
    draft = st.session_state.get('guided_draft', {'lag_ms': 10, 'repeats': 1, 'prediction': 'I am unsure'})
    st.session_state.setdefault('guided_lag', draft['lag_ms'])
    st.session_state.setdefault('guided_repeats', draft['repeats'])
    st.session_state.setdefault('guided_prediction', draft['prediction'])
    st.subheader('Same cells. Change the timing.')
    st.write('**Changed variable:** when B fires relative to A’s signal arriving. '
             '**Held constant:** starting strength, neuron properties, delay, pulse size and pair count across conditions.')
    st.radio('Before running, what do you predict for your chosen timing?', PREDICTIONS,
             key='guided_prediction', horizontal=True,
             help='Your prediction is saved with the result. It never changes the simulation.')
    cols = st.columns(3)
    for col, text, lag in zip(cols, ['A arrives first · +10 ms', 'B fires first · −10 ms', 'Same time · 0 ms'], [10, -10, 0]):
        col.button(text, on_click=_preset, args=(lag,), key=f'guided_preset_{lag}', width='stretch')
    revision = st.session_state.setdefault('guided_revision', 0)
    value = _editor(lag_ms=st.session_state.guided_lag, revision=revision,
                    default=None, key='guided_timing_editor')
    if accept_editor(value, revision):
        st.session_state.guided_lag = value['lag_ms']
        _timing_changed()
        st.rerun()
    with st.expander('Timing slider and repetition settings'):
        st.slider('B spike minus A signal arrival (ms)', -40, 40, step=1,
                  key='guided_lag', on_change=_timing_changed)
        st.slider('Spike pairs per condition', 1, 20, key='guided_repeats')
        st.caption('Start with one pair. Repeated pairs are 400 ms apart; weights and the rule’s '
                   'decaying traces carry forward within each condition. Every comparison starts fresh.')
    config = TimingConfig(st.session_state.guided_lag, st.session_state.guided_repeats)
    # Widget keys are cleaned up when a different lesson step is rendered.
    st.session_state.guided_draft = {'lag_ms': config.lag_ms, 'repeats': config.repeats,
                                    'prediction': st.session_state.guided_prediction}
    st.caption(f'PROPOSED RUN · B minus arrival: {config.lag_ms:+d} ms · {config.repeats} pair(s) per condition')
    if st.button('Run and compare', type='primary', key='guided_run'):
        with st.spinner('Calculating four independent conditions and frozen transmission probes…'):
            result = run_experiment(config)
        st.session_state.guided_experiment = result
        st.session_state.guided_recorded_prediction = st.session_state.guided_prediction
        st.session_state.guided_branch = 'chosen'
        st.session_state.guided_pair = 1
    result = st.session_state.get('guided_experiment')
    if result is None:
        st.info('Choose a timing, make a prediction if you wish, then press Run and compare. '
                'Recorded activity appears after the calculation.')
        return
    st.divider()
    st.subheader('Your measured result')
    _recorded_caption(result)
    if result.config != config:
        st.warning('Settings have changed. The result below is the previous recording; '
                   'press Run and compare to calculate the proposed settings.')
    summary = result.runs['chosen'].summary()
    cols = st.columns(3)
    cols[0].metric('Starting strength', f'{INITIAL_WEIGHT_NA:.6f} nA')
    cols[1].metric('Final strength', f"{summary['final_weight_nA']:.6f} nA")
    cols[2].metric('Measured change', f"{summary['change_nA']:+.6f} nA")
    st.write(explanation(result))
    st.caption('nA is a nanoampere. In this model, connection strength sets the size of an arriving synaptic current.')
    cols = st.columns([2, 1])
    branch = cols[0].selectbox('Recording to inspect', list(CONDITIONS), format_func=CONDITIONS.get,
                              key='guided_branch')
    pair = cols[1].selectbox('Recorded pair', list(range(1, result.config.repeats + 1)), key='guided_pair')
    st.iframe(replay_html(replay_payload(result, branch, pair)), height='content',
              alt='Recorded two-neuron timing experiment with playback controls')
    if not embedded:
        st.button('Explain this evidence →', type='primary', key='guided_explain', on_click=_go, args=(2,))


def _recorded_caption(result):
    st.caption(f'RECORDED RUN · B minus A arrival: {result.config.lag_ms:+d} ms · '
               f'{result.config.repeats} pair(s) per condition · 0.5 ms simulation step')


def _evidence(embedded=False):
    st.subheader('What did changing the timing do?')
    result = st.session_state.get('guided_experiment')
    if result is None:
        st.info('Run an experiment first so this explanation can use your measured result.')
        if not embedded:
            st.button('Go to the experiment →', key='guided_no_result', on_click=_go, args=(1,))
        return
    _recorded_caption(result)
    st.caption('YOUR PREDICTION AT RUN TIME · '+st.session_state.guided_recorded_prediction)
    st.write(explanation(result))
    rows = []
    for run in result.runs.values():
        s = run.summary()
        rows.append({'Condition': s['label'], 'B − arrival (ms)': s['measured_lags_ms'][0],
                     'A / B spikes': ' / '.join(map(str, s['spike_counts'])),
                     'Final strength (nA)': s['final_weight_nA'], 'Change (nA)': s['change_nA']})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch',
        column_config={'Final strength (nA)': st.column_config.NumberColumn(format='%.9f'),
                       'Change (nA)': st.column_config.NumberColumn(format='%+.9f')})
    st.caption('Every condition starts at 0.100000 nA with the same number and amplitude of external pulses. '
               'Only the timing or learning switch differs. Far-apart means ±150 ms; '
               'the exponential rule can still give a small change. At zero lag, opposite timing is identical.')
    left, right = st.columns(2)
    with left:
        st.markdown('**Follow the recorded strengths**')
        fig = go.Figure()
        for (key, run), color in zip(result.runs.items(), [charts.CYAN, charts.LILAC, '#a7b9c5', charts.ORANGE]):
            r = run.result
            changes = np.flatnonzero(np.diff(r.weight_history_nA[:, 0]) != 0) + 1
            indices = np.unique(np.concatenate((np.arange(0, len(r.time_ms), 8), changes,
                                                 np.maximum(0, changes-1), [len(r.time_ms)-1])))
            fig.add_trace(go.Scatter(x=r.time_ms[indices], y=r.weight_history_nA[indices, 0],
                name=CONDITIONS[key], mode='lines', line=dict(color=color, shape='hv')))
        _plot(charts.finish(fig, x='Model time (ms)', y='Connection strength (nA)'), 'guided_weight_chart')
    with right:
        st.markdown('**Does transmission actually change?**')
        fig = go.Figure()
        before, after = result.initial_probe, result.runs['chosen'].probe
        for r, label, color in ((before, 'Before training', '#a7b9c5'), (after, 'After your timing', charts.CYAN)):
            fig.add_trace(go.Scatter(x=r.time_ms, y=r.voltage_mV[:, 1] + 65,
                                     name=label, mode='lines', line=dict(color=color)))
        _plot(charts.finish(fig, x='Fresh probe time (ms)', y='B voltage above rest (mV)'), 'guided_probe_chart')
        initial_peak = float(np.max(before.voltage_mV[:, 1]) + 65)
        final_peak = float(np.max(after.voltage_mV[:, 1]) + 65)
        st.write(f'B’s peak above rest: **{initial_peak:.4f} → {final_peak:.4f} mV**.')
        st.caption('Fresh copies start at rest. Only A receives an external pulse; B receives the synaptic '
                   'input. Learning is frozen. B stays below spike threshold in this bounded lesson.')
    with st.container(border=True):
        st.markdown('**What this shows**')
        st.write('Under this rule, relative spike timing can change a connection, and that change '
                 'can alter a later response. The identical-input, learning-disabled copy '
                 'helps separate learning from the effect of stimulation alone.')
        st.markdown('**How this relates to biology**')
        st.write('Bi and Poo studied timing-dependent synaptic changes in cultured rat hippocampal '
                 'neurons. Timing, initial strength and cell type mattered. This is biological '
                 'motivation for the lesson, rather than validation of every parameter we chose.')
        st.markdown('[Read the experiment · Bi & Poo, 1998](https://pubmed.ncbi.nlm.nih.gov/9852584/)')
        st.caption('The circuit demonstrates programmed assumptions. It does not measure a human brain '
                   'or explain all memory. Millisecond spike timing does not prescribe a student’s study schedule.')
    with st.expander('Model details, conventions and vocabulary'):
        st.write('A spike is a recorded threshold crossing. Arrival is that source spike plus '
                 'the 1 ms transmission delay. Plasticity means a change in connection strength.')
        st.write('The engine uses bounded additive all-to-all pair STDP. Positive lag adds '
                 '0.020 × exp(−lag/20) nA; negative lag subtracts 0.021 × exp(lag/20) nA. '
                 'A new equal-time pair contributes zero. Bounds are 0.001–0.350 nA.')
        st.caption('Earlier pairs still contribute via decaying traces. Repeated equal-time pairs can '
                   'therefore leave a tiny residual. The first-pair zero-lag convention is a model choice. '
                   'Transmission uses the strength before any same-time update. '
                   'Chemical release, receptors and ion-channel kinetics are not modeled.')
    st.markdown('**Keep your experiment**')
    cols = st.columns(2)
    cols[0].download_button('Download my experiment note',
        notebook(result, st.session_state.guided_recorded_prediction), 'synapse_timing_note.md',
        'text/markdown', key='guided_note', on_click='ignore', width='stretch')
    cols[1].download_button('Download reproducible experiment JSON', result.json_bytes(),
        'synapse_timing_experiment.json', 'application/json', key='guided_json',
        on_click='ignore', width='stretch')
    st.caption('Download to keep the result after closing the app. Playback and navigation do not train any other workspace.')
    if not embedded:
        st.button('Try a different timing →', key='guided_again', on_click=_go, args=(1,))


def page():
    st.markdown('<div class="eyebrow">SYNAPSE / GUIDED LEARNING LABORATORY</div>', unsafe_allow_html=True)
    st.title('Small experiments. Understandable learning.')
    if not st.session_state.get('guided_started', False):
        _landing()
        return
    st.button('← All guided lessons', key='guided_home', on_click=_home)
    step = st.radio('Your lesson', STEPS, key='guided_step', horizontal=True)
    if step == STEPS[0]: _meet()
    elif step == STEPS[1]: _experiment()
    else: _evidence()
