(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ArenaReplay=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  function frame(data,time){
    const t=Math.min(100,Math.max(0,Number(time)||0)),row=data.row;
    const decision=Boolean(data.ready&&t>=20),feedback=Boolean(data.ready&&t>=35);
    const active=new Set(),counts=Array(data.n).fill(0);
    for(const [when,neuron] of data.spikes){if(when<=t){counts[neuron]++;if(t-when<=1.5)active.add(neuron);}}
    const packets=[];
    for(const [arrival,index,weight] of data.arrivals){
      const edge=data.edges[index],emission=arrival-edge.delay;
      if(t>=emission&&t<arrival)packets.push({index,weight,progress:(t-emission)/edge.delay});
    }
    return {time:t,decision,feedback,action:decision?row.action:null,reward:feedback?row.reward:null,
      position:feedback?row.after:data.position,
      trail:feedback?data.trail.concat([row.after]):data.trail,
      weights:feedback?data.finalWeights:data.initialWeights,
      voltage:data.voltage.length?data.voltage[Math.min(data.voltage.length-1,Math.floor(t/data.dt))]:Array(data.n).fill(data.rest),
      active,counts,packets,
      phase:!data.ready?'Waiting for a calculated move':t<5?'Sensor input':t<20?'Neural response':t<35?'Action execution':'Movement and feedback'};
  }
  return {frame};
});
