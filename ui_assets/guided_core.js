(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.GuidedReplay=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){'use strict';
function frame(d,time){
 const t=Math.max(d.start,Math.min(d.stop,Number(time)||d.start));
 const index=Math.max(0,Math.min(d.time.length-1,Math.floor((t-d.start)/d.dt+1e-8)));
 const counts=[0,0],active=[false,false];
 for(const [when,cell] of d.spikes)if(when<=t){counts[cell]++;active[cell]=t-when<=1.5;}
 const travelling=t>=d.sourceSpike&&t<d.arrival;
 const arrived=t>=d.arrival,posted=t>=d.targetSpike;
 let phase='Waiting for the external pulses.';
 if(counts[0]&&!arrived)phase='A fired. Its signal is travelling toward the connection.';
 if(arrived&&!posted)phase='A’s signal has arrived. B has not fired yet.';
 if(posted&&!arrived)phase='B fired before A’s signal arrived.';
 if(posted&&arrived)phase=d.learning?'Both events recorded. Inspect the connection strength.':'Both events recorded. Learning is disabled.';
 return {time:t,index,counts,active,arrived,posted,travelling,
  progress:travelling?(t-d.sourceSpike)/d.delay:0,phase,
  voltage:d.voltage[index].slice(),weight:d.weights[index],
  changes:d.updates.filter(e=>e.time<=t).length};
}
function nextEvent(d,time){const events=[d.sourceSpike,d.arrival,d.targetSpike,...d.updates.map(x=>x.time),d.stop].sort((a,b)=>a-b);return events.find(t=>t>time+1e-7)??d.stop;}
return {frame,nextEvent};
});
