"""Streamlit workspace; simulation and evaluation live in arena.py."""

from io import BytesIO
import json
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .arena import ArenaSession, World, ACTIONS, SENSOR_NAMES, MAX_MOVES, compare
from .arena_view import arena_payload, arena_html
from . import lab_charts as charts

PRESETS = {'Open board':(), 'Corner walls':((1,1),(1,2),(3,3)), 'Detour challenge':((0,2),(1,2),(2,2),(3,2)), 'Custom':()}


def pause(key_prefix='arena'): st.session_state[key_prefix+'_running'] = False


def preset_changed(key_prefix='arena'):
    pause(key_prefix)
    st.session_state[key_prefix+'_walls'] = [r*5+c for r,c in PRESETS[st.session_state[key_prefix+'_preset']]]
    st.session_state[key_prefix+'_hazards'] = []


def page(embedded=False, *, neurons=50, key_prefix='arena', lesson_focus=None):
    k=lambda name:key_prefix+'_'+name
    pause_active=lambda:pause(key_prefix)
    preset_active=lambda:preset_changed(key_prefix)
    if key_prefix not in st.session_state:
        st.session_state[key_prefix] = ArenaSession(n_neurons=neurons)
        st.session_state[key_prefix].begin_episode()
        st.session_state[k('running')] = False
    active=st.session_state[key_prefix]
    if active.profile.n_neurons!=neurons: raise ValueError('Movement workspace and controller sizes disagree.')
    if st.session_state.pop(k('refresh_editor'),False):
        for name in ('preset','walls','hazards','max_steps','seed','mode','feedback','custom_pair','custom_start','custom_goal'):
            st.session_state.pop(k(name),None)
    st.session_state.setdefault(k('walls'),[r*5+c for r,c in active.world.walls])
    st.session_state.setdefault(k('hazards'),[r*5+c for r,c in active.world.hazards])
    preset=next((name for name,walls in PRESETS.items() if walls==active.world.walls and not active.world.hazards),'Custom')
    filename='synapse_arena' if neurons==50 else 'synapse_movement_100'
    if not embedded:
        st.markdown('<div class="eyebrow">MOVEMENT ARENA / FOUR NEURAL ACTIONS</div>',unsafe_allow_html=True)
        st.title('Give the circuit somewhere to go.')
    else:
        st.subheader('Explore a small simulated world')
    st.caption(f'A separate {neurons}-cell controller senses goal direction and nearby danger. Its action-cell voltages choose a move; '
               'the world then returns feedback. The earlier two-choice session stays separate.')
    with st.expander('Edit the arena or create a fresh controller'):
        st.caption('Apply creates a fresh arena controller and resets its learned weights/history. Download its checkpoint first to keep it. '
                   'Alternatively, evaluate the edited map with the existing weights below.')
        st.selectbox('Map preset',list(PRESETS),index=list(PRESETS).index(preset),key=k('preset'),on_change=preset_active)
        with st.form(k('world_settings')):
            left,right=st.columns(2)
            cell_label=lambda i:f'Row {i//5+1}, column {i%5+1}'
            with left:
                walls=st.multiselect('Wall cells',range(25),max_selections=12,format_func=cell_label,key=k('walls'))
                hazards=st.multiselect('Hazard cells',range(25),max_selections=8,format_func=cell_label,key=k('hazards'))
                max_steps=st.slider('Maximum moves per episode',4,32,active.world.max_steps,1,key=k('max_steps'))
            with right:
                seed=st.number_input('Arena seed',min_value=0,max_value=2**32-1,value=active.seed,step=1,key=k('seed'))
                modes=['learning','learning_disabled','random_feedback']
                mode=st.selectbox('Arena learning condition',modes,index=modes.index(active.mode),key=k('mode'))
                feedback=st.selectbox('Environmental feedback',['shaped','sparse'],index=['shaped','sparse'].index(active.world.feedback),key=k('feedback'),
                    help='Shaped adds distance progress feedback. Sparse uses goal/hazard/collision outcomes and a small step cost.')
                custom=st.checkbox('Set the first start and goal myself',key=k('custom_pair'))
                start=st.selectbox('First agent cell',range(25),index=12,format_func=cell_label,key=k('custom_start'))
                goal=st.selectbox('First goal cell',range(25),index=13,format_func=cell_label,key=k('custom_goal'))
            apply=st.form_submit_button('Apply map and reset arena',width='stretch',on_click=pause_active)
        if apply:
            try:
                world=World(tuple((i//5,i%5) for i in walls),tuple((i//5,i%5) for i in hazards),max_steps,feedback)
                replacement=ArenaSession(int(seed),world=world,mode=mode,n_neurons=neurons)
                replacement.begin_episode((start//5,start%5),(goal//5,goal%5)) if custom else replacement.begin_episode()
                st.session_state[key_prefix]=replacement; pause_active()
                st.session_state.pop(k('eval'),None)
                st.success('New arena applied. Learned weights and arena history reset.')
            except (ValueError,FloatingPointError) as exc: st.error(f'Arena was not changed: {exc}')
    session=st.session_state[key_prefix]
    st.caption(f'ACTIVE ARENA · seed {session.seed} · {session.mode} · {session.world.feedback} feedback · '
               f'{len(session.world.walls)} walls / {len(session.world.hazards)} hazards · '
               f'0.5 ms simulation step · {len(session.engine.weights)} connections / {len(session.engine.selected)} adaptive')
    frozen=st.toggle('Frozen greedy play',value=False,key=k('frozen'),on_change=pause_active,
                     help='Disable learning and exploration for subsequent live moves. Training batches are disabled while this is on.')
    controls=st.columns([1,1,1,1.4,1.7])
    remaining=MAX_MOVES-len(session.records)
    if controls[0].button('Start moving',key=k('start'),disabled=st.session_state[k('running')] or remaining==0,width='stretch',type='primary'):
        st.session_state[k('running')]=True
        st.session_state[k('last_advance')]=0.0
    controls[1].button('Pause',key=k('pause'),on_click=pause_active,disabled=not st.session_state[k('running')],width='stretch')
    if controls[2].button('Step move',key=k('step'),disabled=remaining==0,width='stretch'):
        pause_active()
        try: session.step(frozen=frozen,record=True)
        except (ValueError,FloatingPointError) as exc: st.error(str(exc))
    if controls[3].button('Train 20 episodes',key=k('train'),disabled=remaining==0 or frozen,width='stretch'):
        pause_active()
        try:
            with st.spinner('Calculating 20 episodes; weights update only from delivered feedback…'): session.train(20)
        except (ValueError,FloatingPointError) as exc: st.error(str(exc))
    controls[4].caption('Live: one move per ~7 seconds so its six-second recording can finish. '
                        'Train computes a batch. Episode resets clear neural dynamics and keep weights.')

    @st.fragment(run_every=7.0 if st.session_state[k('running')] else None)
    def live():
        s=st.session_state[key_prefix]
        if st.session_state[k('running')] and time.monotonic()-st.session_state.get(k('last_advance'),0)>=7:
            try: s.step(frozen=st.session_state[k('frozen')],record=True)
            except (ValueError,FloatingPointError) as exc:
                pause_active();st.error(str(exc));st.rerun()
            st.session_state[k('last_advance')]=time.monotonic()
            if len(s.records)>=MAX_MOVES: pause_active();st.rerun()
        cols=st.columns(4)
        cols[0].metric('Completed episodes',len(s.episodes))
        cols[1].metric('Calculated moves',len(s.records))
        recent=s.episodes[-20:]
        cols[2].metric('Recent goals reached',f"{sum(e['success'] for e in recent)} / {len(recent)}")
        cols[3].metric('Current episode',f'{s.episode_steps} / {s.world.max_steps} moves')
        st.caption('These counts summarize completed simulation, including exploration; frozen evaluation is below.')
        payload=arena_payload(s,lesson_focus=lesson_focus);html=arena_html(payload)
        st.iframe(html,height='content',tab_index=0,alt='Recorded arena movement with actual neural activity')
        if s.last_window is not None:
            w=s.last_window
            with st.expander('Inspect the completed move and learned sensor preferences'):
                neuron=st.selectbox('Arena neuron',range(neurons),index=session.profile.motors[0][0],key=k('neuron'),format_func=lambda i:f'N{i}')
                fig=charts.voltage_chart(w.time_ms-w.time_ms[0],w.voltage_mV,neuron,threshold=s.engine.network.neuron.threshold_mV)
                st.plotly_chart(fig,width='stretch',theme=None,key=k('voltage'))
                means=s.engine.weights[:s.profile.adaptive_count].reshape(8,len(s.profile.sensors[0]),4,len(s.profile.motors[0])).mean(axis=(1,3))
                fig=go.Figure(go.Heatmap(z=means,x=ACTIONS,y=SENSOR_NAMES,colorscale='Viridis',colorbar_title='nA'))
                st.plotly_chart(charts.finish(fig,height=340),width='stretch',theme=None,key=k('preferences'))
                st.caption('Means of actual adaptive weights: eight sensor channels → four action populations. '
                           'Action scores are measured before execution currents and outcome feedback.')
                st.json(s.records[-1])
            cols=st.columns(2)
            cols[0].download_button('Download move replay HTML',html,filename+'_move.html','text/html',on_click='ignore')
            out=BytesIO();np.savez_compressed(out,**vars(w))
            cols[1].download_button('Download move trace NPZ',out.getvalue(),filename+'_move.npz','application/octet-stream',on_click='ignore')
    live()

    st.subheader('Test what was learned')
    st.caption('Runs independent copies with frozen weights, greedy neural choices and no exploration. '
               'All controllers receive the same reserved start/goal pairs. Random and simple greedy baselines use the same sensors. '
               'The active arena is preserved. Walls can require detours this reactive controller has not learned.')
    cols=st.columns(3)
    count=cols[0].selectbox('Evaluation journeys',[24,12,4,40],key=k('eval_count'),on_change=pause_active)
    evaluation_seed=cols[1].number_input('Evaluation seed',min_value=0,max_value=2**32-1,value=10007,step=1,key=k('eval_seed'),on_change=pause_active)
    changed=cols[2].checkbox('Evaluate the edited map',key=k('eval_changed'),on_change=pause_active,
        help='Uses the editor values without applying them to the active arena. Weights stay frozen; this tests transfer, not adaptation.')
    if st.button('Run frozen evaluation',key=k('evaluate'),type='primary',on_click=pause_active):
        pause_active()
        try:
            world=World(tuple((i//5,i%5) for i in walls),tuple((i//5,i%5) for i in hazards),max_steps,feedback) if changed else session.world
            with st.spinner('Evaluating trained weights, reset weights, random movement and greedy sensors…'):
                result=compare(session,count,int(evaluation_seed),world)
            st.session_state[k('eval')]=result
        except (ValueError,FloatingPointError) as exc: st.error(f'Evaluation was not run: {exc}')
    result=st.session_state.get(k('eval'))
    if result:
        st.caption(f"SAVED EVALUATION · source seed {result['training_seed']} · after {result['training_episodes']} episodes / "
                   f"{result['training_moves']} moves · evaluation seed {result['evaluation_seed']} · "
                   f"{len(result['world']['walls'])} walls / {len(result['world']['hazards'])} hazards. Continuing training does not change this saved result.")
        labels={'trained':'Current neural weights','reset_weights':'Reset to initial weights','random':'Random movement','greedy_sensors':'Simple greedy sensors'}
        st.dataframe(pd.DataFrame([{'controller':labels[name],'goals reached':f"{r['successes']} / {r['cases']}",
                                  'mean moves':round(r['mean_steps'],2),'collisions':r['collisions'],'hazard endings':r['hazard_endings']}
                                 for name,r in result['conditions'].items()]),hide_index=True,width='stretch')
        condition=st.selectbox('Inspect evaluation controller',list(labels),format_func=labels.get,key=k('eval_controller'))
        journeys=result['conditions'][condition]['journeys']
        index=st.selectbox('Evaluation journey',range(len(journeys)),format_func=lambda i:f'Journey {i+1}',key=k('eval_journey'))
        journey=journeys[index]
        st.caption(f"{result['conditions'][condition]['cases']} evaluation cases, "
                   f"{result['conditions'][condition].get('unique_pairs',len(journeys))} unique start/goal pairs. "
                   'Small edited maps may repeat pairs to fill the requested case count.')
        path=np.asarray(journey['path']);fig=go.Figure()
        fig.add_trace(go.Scatter(x=path[:,1]+1,y=path[:,0]+1,mode='lines+markers',name='Calculated path',line_color=charts.CYAN))
        for name,points,symbol,color in [('Walls',result['world']['walls'],'square','#64798b'),('Hazards',result['world']['hazards'],'x','#ee8d95'),('Goal',[journey['goal']],'star','#e7c479')]:
            if points:
                points=np.asarray(points);fig.add_trace(go.Scatter(x=points[:,1]+1,y=points[:,0]+1,mode='markers',name=name,marker=dict(symbol=symbol,size=18,color=color)))
        fig=charts.finish(fig,height=370,x='Column',y='Row');fig.update_xaxes(range=[.5,5.5],dtick=1);fig.update_yaxes(range=[5.5,.5],dtick=1,scaleanchor='x',scaleratio=1)
        st.plotly_chart(fig,width='stretch',theme=None,key=k('eval_path'))
        st.caption(f"{journey['steps']} moves · {journey['collisions']} collisions · goal reached: {journey['success']}. "
                   'This is a measured route; no route planner supplies neural actions.')
        st.download_button('Download frozen evaluation JSON',json.dumps(result,indent=2,allow_nan=False),filename+'_evaluation.json','application/json',on_click='ignore')
    with st.expander('Save or restore the arena'):
        st.caption('Arena checkpoints are separate from the sidebar two-choice checkpoint. '
                   'They preserve learned weights, complete neural/world state, RNG and histories; dense replay is excluded.')
        st.download_button('Download arena checkpoint',session.checkpoint(),filename+'_checkpoint.json','application/json',on_click='ignore')
        st.download_button('Download arena move history CSV',pd.DataFrame(session.records).to_csv(index=False),filename+'_moves.csv','text/csv',on_click='ignore')
        upload=st.file_uploader('Arena checkpoint JSON',type=['json'],key=k('upload'))
        if st.button('Restore arena checkpoint',disabled=upload is None,key=k('restore')):
            pause_active()
            try:
                replacement=ArenaSession.from_checkpoint(upload.getvalue())
                if replacement.profile.n_neurons!=neurons: raise ValueError(f'This workspace needs a {neurons}-cell arena checkpoint.')
                st.session_state[key_prefix]=replacement;st.session_state[k('refresh_editor')]=True
                st.session_state.pop(k('eval'),None);st.rerun()
            except (ValueError,FloatingPointError) as exc: st.error(f'Arena checkpoint was not loaded: {exc}')
    st.info('Train first on an open board. The first 40 episodes use adjacent goals, the next 40 goals up to two cells away, '
            'then up to four. Shaped feedback rewards distance progress and penalizes collisions. Sparse feedback removes progress shaping. '
            'Hazards end an episode. This is an engineered reactive controller, not learned vision or general route planning.')
