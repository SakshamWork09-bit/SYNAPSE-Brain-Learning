"""Custom signal editors and measured memory experiments in Streamlit."""

from dataclasses import asdict
from io import BytesIO
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .memory_lab import (MemoryModel,Task,Signal,sequence,teach,probe,evaluate,comparison,interference,
                         SECOND_PATTERNS,MIN_MARGIN_MV,workbench_bytes,load_workbench)
from .memory_view import payload,html
from . import lab_charts as charts


def new_lab(kind,seed=7,task=None,revision=0):
    return {'model':MemoryModel(kind,seed),'task':task or Task.defaults(kind),'snapshot':None,
            'revision':revision,'query':None,'evaluation':None,'comparison':None,'interference':None}


def edit_pixels(name,default,key):
    st.caption(name)
    values=[]
    for row in range(3):
        cols=st.columns(3)
        for col in range(3):
            i=row*3+col
            values.append(int(cols[col].checkbox(f'{row+1},{col+1}',value=bool(default[i]),key=f'{key}_{i}')))
    return tuple(values)


def page():
    st.markdown('<div class="eyebrow">PATTERN & SEQUENCE LAB / FROZEN MEMORY TESTS</div>',unsafe_allow_html=True)
    st.title('Teach a response. Test what stays.')
    st.caption('Create two drawings or short A/B/C sequences. Supervised teaching changes response connections; '
               'frozen probes use only the signal and learned weights. This is a separate 50-cell experimental profile.')
    kind=st.radio('Input type',['pattern','sequence'],horizontal=True,key='memory_kind',
                  format_func=lambda x:'Draw patterns' if x=='pattern' else 'Timed sequences')
    if 'memory_labs' not in st.session_state:st.session_state.memory_labs={}
    labs=st.session_state.memory_labs
    if kind not in labs:labs[kind]=new_lab(kind)
    lab=labs[kind];task=lab['task'];model=lab['model'];rev=lab['revision']
    with st.expander('Create your examples or reset this memory',expanded=model.presentations==0):
        st.caption('Example 1 teaches Response A; example 2 teaches Response B. Applying creates fresh weights. '
                   'Pattern and sequence memories are separate. Save a workbench to keep custom examples and weights.')
        with st.form(f'memory_task_{kind}'):
            cols=st.columns(2)
            if kind=='pattern':
                with cols[0]:a=edit_pixels('Example 1 → Response A',task.prototypes[0],f'memory_edit_{kind}_{rev}_a')
                with cols[1]:b=edit_pixels('Example 2 → Response B',task.prototypes[1],f'memory_edit_{kind}_{rev}_b')
            else:
                a=cols[0].text_input('Example 1 → Response A',''.join(task.prototypes[0]),key=f'memory_edit_{kind}_{rev}_a')
                b=cols[1].text_input('Example 2 → Response B',''.join(task.prototypes[1]),key=f'memory_edit_{kind}_{rev}_b')
                st.caption('Use 2–6 symbols from A, B and C. Defaults ABBA/BABA have the same counts and final two symbols.')
            seed=st.number_input('Memory seed',min_value=0,max_value=2**32-1,value=model.seed,step=1,key=f'memory_seed_{kind}_{rev}')
            apply=st.form_submit_button('Apply examples and reset memory',width='stretch')
        if apply:
            try:
                edited=Task(kind,(a,b)) if kind=='pattern' else Task(kind,(sequence(a).content,sequence(b).content))
                labs[kind]=new_lab(kind,int(seed),edited,rev+1);st.rerun()
            except ValueError as exc:st.error(f'Memory was not reset: {exc}')
    st.caption(f'ACTIVE {kind.upper()} MEMORY · seed {model.seed} · {model.presentations} teaching presentations · '
               f'weights {model.fingerprint()[:12]} · 50 cells / 196 links / 172 teachable links')
    controls=st.columns([1,1.5,1.7])
    epochs=controls[0].selectbox('Teaching epochs',[32,16,64,8],key=f'memory_epochs_{kind}')
    condition=controls[1].selectbox('Teaching condition',['teaching','disabled','shuffled'],key=f'memory_condition_{kind}',
        format_func=lambda x:{'teaching':'Correct responses','disabled':'Learning disabled','shuffled':'Conflicting teachers (balanced)'}[x])
    controls[2].caption('16 distinct training signals, each shown twice per epoch. '
                       'A batch delta rule fits the response-voltage difference. This is supervised readout learning, not STDP.')
    if st.button('Teach current examples',key='memory_teach',type='primary'):
        try:
            previous=model.clone()
            with st.spinner('Computing spiking features and teaching response connections…'):teach(model,task,epochs=epochs,condition=condition,seed=model.seed)
            lab['snapshot']=previous
            st.success(f'Taught {epochs*32} presentations. Frozen queries below do not teach.')
        except (ValueError,FloatingPointError) as exc:st.error(f'Teaching was not run: {exc}')
    st.subheader('Ask the frozen circuit')
    with st.form(f'memory_query_form_{kind}'):
        source=st.selectbox('Query signal',['Example 1','Example 2','Custom signal'],key=f'memory_query_source_{kind}')
        if kind=='pattern':
            custom=st.multiselect('Custom lit pixels',range(9),default=[0,3,6,7,8],format_func=lambda i:f'Row {i//3+1}, column {i%3+1}',key='memory_custom_pixels')
        else:custom=st.text_input('Custom sequence','ABBA',key='memory_custom_sequence')
        cols=st.columns(2)
        onset=cols[0].slider('Query onset (ms)',8.,16.,12.,.5,key=f'memory_query_onset_{kind}')
        gap=cols[1].slider('Symbol spacing (ms)',12.,30.,20.,.5,key=f'memory_query_gap_{kind}',disabled=kind=='pattern')
        run=st.form_submit_button('Run frozen query',type='primary',width='stretch')
    if run:
        try:
            content=task.prototypes[0 if source=='Example 1' else 1] if source!='Custom signal' else tuple(int(i in custom) for i in range(9)) if kind=='pattern' else sequence(custom).content
            signal=Signal(kind,content,onset,gap)
            snap=model.clone();initial=MemoryModel(kind,model.seed)
            lab['query']={'current':(snap,probe(snap,signal,record=True)),
                          'initial':(initial,probe(initial,signal,record=True)),'presentations':model.presentations}
        except (ValueError,FloatingPointError) as exc:st.error(f'Query was not run: {exc}')
    if lab['query']:
        q=lab['query'];branch=st.radio('Recorded query weights',['current','initial'],horizontal=True,key=f'memory_query_branch_{kind}',
            format_func=lambda x:'Weights at query time' if x=='current' else 'Initial weights')
        snapshot,result=q[branch]
        st.caption(f"RECORDED QUERY · {snapshot.presentations} presentations at capture · weights {snapshot.fingerprint()[:12]}. "
                   'Later teaching does not change this recording. No expected response is passed to inference.')
        data=payload(snapshot,result);recording=html(data)
        st.iframe(recording,height='content',tab_index=0,alt='Frozen pattern or sequence probe and actual neural response')
        cols=st.columns(3)
        prediction=result['prediction']
        cols[0].metric('Completed probe response','No clear response' if prediction is None else 'A' if prediction==0 else 'B')
        cols[1].metric('A − B voltage',f"{result['margin_mV']:+.4f} mV")
        cols[2].metric('Weight changes in probe','0')
        st.caption(f'Margins below {MIN_MARGIN_MV:g} mV abstain. This threshold is an engineering choice, not a confidence probability.')
        with st.expander('Response traces and learned strengths'):
            w=result['window'];fig=go.Figure()
            for ids,color,name in (((45,46),charts.CYAN,'Response A'),((47,48),charts.LILAC,'Response B')):
                fig.add_trace(go.Scatter(x=w.time_ms,y=w.voltage_mV[:,ids].mean(axis=1),mode='lines',name=name,line_color=color))
            fig.add_vline(x=result['signal'].readout_ms,line_dash='dash')
            st.plotly_chart(charts.finish(fig,x='Time (ms)',y='Mean response voltage (mV)'),width='stretch',theme=None,key='memory_response_trace')
            st.json({'signal':asdict(result['signal']),'scores_mV':result['scores_mV'],'margin_mV':result['margin_mV']})
            names=[f'Pixel {i//2+1} {"ON" if i%2 else "OFF"}' for i in range(18)]+[f'{symbol} +{1+10*tap} ms' for symbol in 'ABC' for tap in range(8)]+['Bias']
            fig=go.Figure(go.Heatmap(z=snapshot.weights,x=['A','B'],y=names,colorscale='Viridis',colorbar_title='nA'))
            st.plotly_chart(charts.finish(fig,height=650),width='stretch',theme=None,key='memory_weights')
        cols=st.columns(3)
        cols[0].download_button('Query replay HTML',recording,'synapse_memory_query.html','text/html',on_click='ignore')
        cols[1].download_button('Query data JSON',json.dumps(data,allow_nan=False),'synapse_memory_query.json','application/json',on_click='ignore')
        out=BytesIO();np.savez_compressed(out,**vars(result['window']))
        cols[2].download_button('Query trace NPZ',out.getvalue(),'synapse_memory_query.npz','application/octet-stream',on_click='ignore')
    else:
        st.iframe(html(payload(model)),height='content',tab_index=0,alt='Pattern and sequence circuit waiting for a query')

    st.subheader('Recognition under changes')
    st.caption('Each test uses 16 balanced frozen queries at timings absent from training. Noise flips pixels or substitutes symbols. '
               'Scores count agreement with the originating template label; ambiguous corruptions are marked separately. '
               'The prototype baseline stores the two example contents explicitly.')
    if st.button('Test clean and noisy signals',key='memory_evaluate'):
        with st.spinner('Probing unchanged weights at three noise levels…'):
            lab['evaluation']={str(n):evaluate(model,task,noise=n) for n in (0,1,2)}
    if lab['evaluation']:
        ev=lab['evaluation'];first=ev['0']
        st.caption(f"SAVED TEST · {first['presentations']} teaching presentations · weights {first['weight_sha256'][:12]} · seed {first['test_seed']}")
        st.dataframe(pd.DataFrame([{'changed pixels/symbols':n,'origin-label matches':f"{r['origin_correct']} / {r['cases']}",
             'no clear response':r['abstentions'],'ambiguous cases':r['ambiguous_cases'],
             'unambiguous matches':f"{r['unambiguous_correct']} / {r['unambiguous_cases']}",
             'prototype baseline':f"{r['prototype_baseline_correct']} / {r['unambiguous_cases']}"} for n,r in ev.items()]),hide_index=True,width='stretch')
        st.download_button('Download frozen noise tests',json.dumps(ev,indent=2,allow_nan=False),'synapse_memory_noise.json','application/json',on_click='ignore')
    with st.expander('Compare teaching with controls'):
        st.caption('Fresh independent models share seed, input signals, initial weights and presentation budgets. '
                   'Conflicting teaching assigns both responses to each exact signal, balancing the labels. Your active model stays intact.')
        if st.button('Run matched memory controls',key='memory_compare'):
            with st.spinner('Teaching and testing independent control models…'):
                result,_=comparison(task,model.seed,epochs)
            lab['comparison']=result
        if lab['comparison']:
            c=lab['comparison']
            st.caption(f"SAVED COMPARISON · seed {c['seed']} · {c['epochs']} epochs · fresh models, not the active trained state")
            st.dataframe(pd.DataFrame([{'condition':name,**{f'{n} changes':f"{r[str(n)]['origin_correct']} / 16" for n in (0,1,2)}}
                                       for name,r in c['conditions'].items()]),hide_index=True,width='stretch')
            st.download_button('Download memory controls JSON',json.dumps(c,indent=2,allow_nan=False),'synapse_memory_controls.json','application/json',on_click='ignore')

    st.subheader('Does new teaching disturb old responses?')
    mode=st.radio('Interference experiment',['new_pair','reversal'],horizontal=True,key=f'memory_interference_mode_{kind}',
                  format_func=lambda x:'Teach a second pair' if x=='new_pair' else 'Reverse the existing responses')
    with st.form(f'memory_interference_form_{kind}'):
        if mode=='new_pair':
            cols=st.columns(2)
            if kind=='pattern':
                with cols[0]:a2=edit_pixels('New example → Response A',SECOND_PATTERNS[0],f'memory_newpair_{kind}_a')
                with cols[1]:b2=edit_pixels('New example → Response B',SECOND_PATTERNS[1],f'memory_newpair_{kind}_b')
            else:
                a2=cols[0].text_input('New sequence → Response A','BABC',key='memory_new_sequence_a')
                b2=cols[1].text_input('New sequence → Response B','ABBC',key='memory_new_sequence_b')
            st.caption('Defaults are similar new inputs with changed associations. Similarity can create interference; rehearsal may help or fail.')
        else:st.caption('Identical signals receive opposite responses. Both assignments cannot be satisfied simultaneously.')
        run_change=st.form_submit_button('Run interference comparison',width='stretch')
    if run_change:
        try:
            second=Task(kind,task.prototypes[::-1]) if mode=='reversal' else Task(kind,(a2,b2)) if kind=='pattern' else Task(kind,(sequence(a2).content,sequence(b2).content))
            with st.spinner('Comparing new teaching only with matched-budget rehearsal…'):
                result,new_only,rehearsed=interference(model,task,second,epochs=epochs,seed=model.seed)
            lab['interference']={'result':result,'source':model.clone(),'new_only':new_only,'rehearsal':rehearsed}
        except (ValueError,FloatingPointError) as exc:st.error(f'Interference was not run: {exc}')
    if lab['interference']:
        saved=lab['interference'];r=saved['result']
        st.caption(f"SAVED INTERFERENCE · source weights {r['source_weight_sha256'][:12]} · "
                   f"{r['new_presentations']} new-only / {r['rehearsal_presentations']} rehearsal presentations. Active weights change only with an apply button.")
        st.dataframe(pd.DataFrame([{'phase':name,'old responses retained':f"{r[name]['old']['origin_correct']} / 16",
                                  'new responses learned':f"{r[name]['new']['origin_correct']} / 16"} for name in ('before','new_only','rehearsal')]),hide_index=True,width='stretch')
        cols=st.columns(3)
        for i,(key,label) in enumerate((('new_only','Use new-only weights'),('rehearsal','Use rehearsal weights'),('source','Restore earlier snapshot'))):
            if cols[i].button(label,key=f'memory_apply_{key}'):
                lab['snapshot']=saved['source'].clone();lab['model']=saved[key].clone();st.rerun()
        st.caption('Original examples above stay as retention references after applying a model. Restoring a snapshot replaces weights; it is not biological recovery.')
        st.download_button('Download interference JSON',json.dumps(r,indent=2,allow_nan=False),'synapse_memory_interference.json','application/json',on_click='ignore')
    with st.expander('Save or restore this memory'):
        model=lab['model']
        st.download_button('Download memory workbench',workbench_bytes(task,model,lab['snapshot']),'synapse_memory_workbench.json','application/json',on_click='ignore')
        st.download_button('Download frozen memory model',model.json_bytes(),'synapse_memory_model.json','application/json',on_click='ignore')
        upload=st.file_uploader('Memory workbench JSON',type=['json'],key=f'memory_upload_{kind}')
        if st.button('Restore memory workbench',disabled=upload is None,key='memory_restore'):
            try:
                loaded_task,loaded,snapshot=load_workbench(upload.getvalue())
                if loaded.kind!=kind:raise ValueError('switch Input type to match the saved workbench first')
                replacement=new_lab(kind,loaded.seed,loaded_task,rev+1);replacement['model']=loaded;replacement['snapshot']=snapshot
                labs[kind]=replacement;st.rerun()
            except (ValueError,FloatingPointError) as exc:st.error(f'Memory was not loaded: {exc}')
    st.info('This is supervised association, not autonomous discovery. Spatial ON/OFF encoding and temporal delay lines are engineered. '
            'The readout can forget or fail on new timing/noise; it does not learn a general grammar or reconstruct a missing drawing. '
            'Each presentation resets neural dynamics. Learned associations are stored in weights.')
