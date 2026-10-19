(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.MemoryReplay=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){'use strict';
  function frame(data,time){
    const t=Math.max(0,Math.min(data.duration,Number(time)||0)),revealed=Boolean(data.ready&&t>=data.readoutTime);
    const counts=Array(50).fill(0),active=new Set(),packets=[];
    for(const [when,cell] of data.spikes){if(when<=t){counts[cell]++;if(t-when<=1.5)active.add(cell);}}
    for(const [arrival,index,weight] of data.arrivals){const edge=data.edges[index],emission=arrival-edge.delay;if(t>=emission&&t<arrival)packets.push({index,weight,progress:(t-emission)/edge.delay});}
    return {time:t,revealed,prediction:revealed?data.prediction:null,scores:revealed?data.scores:null,
      active,counts,packets,voltage:data.voltage.length?data.voltage[Math.min(data.voltage.length-1,Math.floor(t/data.dt))]:Array(50).fill(data.rest),
      phase:!data.ready?'Waiting for a calculated probe':revealed?'Readout complete · weights frozen':'Input and neural response · weights frozen'};
  }return {frame};
});
