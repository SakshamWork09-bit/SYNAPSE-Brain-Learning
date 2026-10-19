/* Pure playback queries. Time selects recorded data; it never executes a model. */
(function(root) {
  'use strict';
  function frameAt(data, requestedTime) {
    const time=Math.max(0,Math.min(data.duration,requestedTime));
    const ready=data.ready, probe=data.kind==='probe';
    const decision=ready && !probe && time>=data.decisionTime;
    const feedback=ready && !probe && time>=data.feedbackTime;
    const weights=feedback?data.finalWeights:data.initialWeights;
    const voltage=ready?data.voltage[Math.min(data.voltage.length-1,Math.floor((time+1e-8)/data.dt))]:data.initialVoltage;
    const flashes=new Set();
    for (const [t,n] of data.spikes) if(t<=time && time-t<=1.5)flashes.add(n);
    const packets=[];
    for(const [arrival,edge,weight] of data.arrivals) {
      const emission=arrival-data.edges[edge].delay;
      if(emission<=time && time<arrival)packets.push({edge,progress:(time-emission)/(arrival-emission),weight});
    }
    const changed=[];
    if(feedback)for(let i=0;i<weights.length;i++) {
      const delta=weights[i]-data.initialWeights[i];
      if(Math.abs(delta)>1e-12)changed.push({edge:i,delta});
    }
    let phase='Waiting for a calculated experience';
    if(ready)phase=probe?(time<data.stimulus.start?'Before manual pulse':time<data.stimulus.stop?'Manual pulse interval':'Response and decay'):
      time<5?'Sensory input':time<25?'Circuit processing':time<30?'Chosen action executes':time<35?'Awaiting outcome':'Feedback and retained state';
    return {time,decision,feedback,weights,voltage,flashes,packets,changed,phase,
            action:decision?data.action:null,reward:feedback?data.reward:null,
            delivered:feedback?data.feedback:null};
  }
  function positions(data) {
    const nodes=[];
    // Four columns show engineered cell roles, not anatomical locations.
    data.groups.forEach((g,gi)=>{
      const column=gi<2?0:gi<4?1:gi<6?2:3;
      const section=gi%2;
      g.neurons.forEach((id,j)=>nodes[id]={x:.09+column*.27,
        y:.12+section*.48+(j+.5)/g.neurons.length*.34,group:gi,color:g.color});
    });
    return nodes;
  }
  function curve(nodes,edge) {
    const a=nodes[edge.source],b=nodes[edge.target];
    const dx=b.x-a.x,dy=b.y-a.y;
    const bend=(edge.source<edge.target?1:-1)*.045;
    return {a,b,c:{x:(a.x+b.x)/2-dy*bend,y:(a.y+b.y)/2+dx*bend}};
  }
  function point(c,t) {
    const u=1-t;
    return {x:u*u*c.a.x+2*u*t*c.c.x+t*t*c.b.x,
            y:u*u*c.a.y+2*u*t*c.c.y+t*t*c.b.y};
  }
  const api={frameAt,positions,curve,point};
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  else root.SynapseReplay=api;
})(typeof window!=='undefined'?window:globalThis);
