"""Interactive views of computed data; all chart functions are read-only."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .laboratory import GROUP_COLORS, GROUP_LABELS, MODE_LABELS
from .integrated import GROUPS

CYAN = '#126d70'
LILAC = '#78579b'
ORANGE = '#b46834'


def finish(fig, *, height=340, x=None, y=None):
    fig.update_layout(template='plotly_white', height=height,
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      font=dict(family='Arial, sans-serif', size=12, color='#284750'),
                      margin=dict(l=40, r=20, t=30, b=40),
                      legend=dict(orientation='h', y=1.16, x=0),
                      xaxis_title=x, yaxis_title=y)
    fig.update_xaxes(gridcolor='#dbe6e1', zerolinecolor='#c0d1ca')
    fig.update_yaxes(gridcolor='#dbe6e1', zerolinecolor='#c0d1ca')
    return fig


def success_chart(records, reversal):
    values = np.array([r['reward'] for r in records], dtype=float)
    y = [100*values[max(0, i-19):i+1].mean() for i in range(len(values))]
    fig = go.Figure(go.Scatter(x=np.arange(1,len(y)+1), y=y, mode='lines',
                               line=dict(color=CYAN, width=3), fill='tozeroy',
                               fillcolor='rgba(115,207,202,0.07)', name='Actual outcome',
                               hovertemplate='Experience %{x}<br>Recent success %{y:.1f}%<extra></extra>'))
    fig.add_hline(y=50, line_dash='dot', line_color='#647581')
    fig.add_vline(x=reversal+0.5, line_dash='dash', line_color=ORANGE)
    fig.update_yaxes(range=[-2,102])
    return finish(fig, x='Experience', y='Success over up to 20 recent experiences (%)')


def preference_chart(records, reversal):
    fig = go.Figure()
    for i, (label, color) in enumerate(zip(('A → 0','A → 1','B → 0','B → 1'),
                                           (CYAN, '#408b8b', LILAC, '#7660b1'))):
        fig.add_trace(go.Scatter(x=np.arange(1,len(records)+1),
                                y=[r['weight_preferences_nA'][i] for r in records],
                                mode='lines', name=label, line=dict(color=color, width=2)))
    fig.add_vline(x=reversal+0.5, line_dash='dash', line_color=ORANGE)
    return finish(fig, x='Experience', y='Mean association → action strength (nA)')


def raster(times, neurons, *, start=None, stop=None, n=50, cursor=None):
    fig = go.Figure(go.Scattergl(x=times, y=neurons, mode='markers',
                                marker=dict(color=CYAN, symbol='line-ns', size=8),
                                hovertemplate='%{x:.2f} ms · N%{y}<extra>Spike</extra>'))
    if start is not None:
        fig.update_xaxes(range=[start,stop])
    fig.update_yaxes(range=[-1,n], dtick=5 if n==50 else 1)
    if cursor is not None:
        fig.add_vline(x=cursor, line_color=ORANGE, line_width=1)
    return finish(fig, height=300, x='Simulation time (ms)', y='Neuron')


def voltage_chart(time_ms, voltage, neuron, *, threshold=None, current_times=None, current=None, cursor=None):
    fig = make_subplots(rows=2 if current is not None else 1, cols=1, shared_xaxes=True,
                        vertical_spacing=0.12)
    fig.add_trace(go.Scatter(x=time_ms, y=voltage[:,neuron], name=f'N{neuron} voltage',
                            mode='lines', line=dict(color=LILAC, width=2)), row=1,col=1)
    if threshold is not None:
        fig.add_hline(y=threshold, line_dash='dot', line_color='#74828d', row=1,col=1)
    fig.update_yaxes(title_text='Voltage (mV)', row=1,col=1)
    if current is not None:
        fig.add_trace(go.Scatter(x=current_times,y=current[:,neuron],name='Synaptic current',
                                mode='lines',line=dict(color=ORANGE,width=2)),row=2,col=1)
        fig.update_yaxes(title_text='Current (nA)',row=2,col=1)
    if cursor is not None:
        fig.add_vline(x=cursor,line_color=ORANGE,line_width=1)
    return finish(fig, height=390, x='Simulation time (ms)')


def weight_matrix(network, weights, *, eligible=False):
    if eligible:
        sources,targets=list(range(10,30)),list(range(40,50))
    else:
        sources=targets=list(range(network.n_neurons))
    matrix=np.zeros((len(targets),len(sources)))
    si={v:i for i,v in enumerate(sources)};ti={v:i for i,v in enumerate(targets)}
    for edge,weight in zip(network.synapses,weights):
        if edge.source in si and edge.target in ti:matrix[ti[edge.target],si[edge.source]]=weight
    colorscale='Viridis' if eligible else 'RdBu_r'
    fig=go.Figure(go.Heatmap(z=matrix,x=sources,y=targets,colorscale=colorscale,
                            zmin=0.002 if eligible else -max(abs(weights)),
                            zmax=0.06 if eligible else max(abs(weights)),
                            colorbar=dict(title='nA'),
                            hovertemplate='N%{x} → N%{y}<br>%{z:.5f} nA<extra></extra>'))
    return finish(fig,height=390,x='Source neuron',y='Receiving neuron')


def neuron_positions(network):
    n=network.n_neurons
    if n==50:
        pos=np.zeros((50,2))
        pos[:10,0]=0;pos[:10,1]=np.linspace(1,-1,10)
        pos[10:30,0]=1;pos[10:30,1]=np.linspace(1.4,-0.4,20)
        pos[30:40,0]=1;pos[30:40,1]=np.linspace(-0.75,-1.6,10)
        pos[40:,0]=2;pos[40:,1]=np.linspace(1,-1,10)
    else:
        angles=np.linspace(0,2*np.pi,n,endpoint=False)
        pos=np.column_stack((np.cos(angles),np.sin(angles)))
    return pos


def network_view(network, weights, *, selected=0, voltage=None, spike_counts=None, flash=()):
    pos=neuron_positions(network)
    fig=go.Figure()
    # Only the inspected cell's incident edges are shown to keep 50 cells legible.
    for negative,color in ((False,'rgba(115,207,202,0.5)'),(True,'rgba(238,171,114,0.65)')):
        xs,ys=[],[]
        for edge,w in zip(network.synapses,weights):
            if (selected in (edge.source,edge.target)) and (w<0)==negative:
                xs.extend([pos[edge.source,0],pos[edge.target,0],None])
                ys.extend([pos[edge.source,1],pos[edge.target,1],None])
        fig.add_trace(go.Scatter(x=xs,y=ys,mode='lines',line=dict(color=color,width=1),
                                hoverinfo='skip',showlegend=False))
    voltage=np.asarray(voltage) if voltage is not None else np.full(network.n_neurons,network.neuron.rest_mV)
    counts=np.asarray(spike_counts) if spike_counts is not None else np.zeros(network.n_neurons,dtype=int)
    groups=list(GROUPS.values()) if network.n_neurons==50 else [tuple(range(network.n_neurons))]
    labels=GROUP_LABELS if network.n_neurons==50 else ('Circuit neurons',)
    for inds,label,color in zip(groups,labels,GROUP_COLORS):
        ids=np.array(inds)
        fig.add_trace(go.Scatter(x=pos[ids,0],y=pos[ids,1],mode='markers',name=label,
                                marker=dict(size=11+np.minimum(counts[ids],6),color=color,
                                            line=dict(color='#10171d',width=1)),
                                customdata=np.column_stack((ids,voltage[ids],counts[ids])),
                                hovertemplate='N%{customdata[0]:.0f}<br>%{customdata[1]:.2f} mV<br>%{customdata[2]:.0f} spikes in shown scope<extra>%{fullData.name}</extra>'))
    fig.add_trace(go.Scatter(x=[pos[selected,0]],y=[pos[selected,1]],mode='markers+text',
                            text=[f'N{selected}'],textposition='middle right',
                            marker=dict(size=26,color='rgba(0,0,0,0)',line=dict(color='white',width=2)),
                            showlegend=False,hoverinfo='skip'))
    if len(flash):
        ids=np.array(flash,dtype=int)
        fig.add_trace(go.Scatter(x=pos[ids,0],y=pos[ids,1],mode='markers',
                                marker=dict(size=23,color='white',opacity=.75),
                                name='Spike near cursor',hoverinfo='skip'))
    finish(fig,height=490)
    fig.update_xaxes(visible=False,range=[-.3,2.4] if network.n_neurons==50 else [-1.3,1.3])
    fig.update_yaxes(visible=False,range=[-1.8,1.65] if network.n_neurons==50 else [-1.3,1.3])
    fig.update_layout(legend=dict(orientation='h',y=-.06,font=dict(size=10)),margin=dict(l=15,r=15,t=15,b=65))
    return fig


def comparison_chart(results,reversal):
    fig=go.Figure()
    for (mode,rows),color in zip(results.items(),(CYAN,LILAC,ORANGE)):
        values=np.convolve([r['reward'] for r in rows],np.ones(20)/20,mode='valid')
        fig.add_trace(go.Scatter(x=np.arange(20,len(rows)+1),y=100*values,name=MODE_LABELS[mode],
                                mode='lines',line=dict(color=color,width=2)))
    fig.add_vline(x=reversal+.5,line_dash='dash',line_color='#e1e7eb')
    fig.add_hline(y=50,line_dash='dot',line_color='#647581')
    fig.update_yaxes(range=[-2,102])
    return finish(fig,height=360,x='Experience',y='Success over last 20 experiences (%)')
