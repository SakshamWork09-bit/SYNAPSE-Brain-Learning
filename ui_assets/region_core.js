(function(root){'use strict';
 function phaseAt(data,time){return data.stages.find(s=>time>=s.start&&time<s.end)||data.stages[data.stages.length-1]||null;}
 function frameAt(data,time,cell){
  const t=Math.max(0,Math.min(data.duration,time)),index=Math.min(data.time.length-1,Math.max(0,Math.floor(t/data.dt+1e-9)));
  const arrived=data.arrivals.filter(a=>a[0]<=t),spikes=data.spikes.filter(s=>s[0]<=t&&s[1]===cell);
  return {time:t,index,phase:phaseAt(data,t),voltage:data.voltage[index]?.[cell]??-65,
    current:data.current[Math.min(index,data.current.length-1)]?.[cell]??0,
    input:data.input[Math.min(index,data.input.length-1)]?.[cell]??0,
    cellSpikes:spikes.length,arrived:arrived.filter(a=>data.edges[a[1]].target===cell).length,
    prediction:t>=data.readout?data.prediction:null,readoutReached:t>=data.readout};
 }
 function positions(data){const p=Array.from({length:100},()=>[0,0]);
  const grid=(cells,x,y,cols,dx,dy)=>cells.forEach((cell,i)=>{p[cell]=[x+(i%cols)*dx,y+Math.floor(i/cols)*dy];});
  grid(data.groups[0].cells,.065,.17,3,.032,.093);grid(data.groups[1].cells,.065,.88,3,.032,.09);
  grid(data.groups[2].cells,.32,.17,6,.029,.087);grid(data.groups[3].cells,.65,.17,2,.037,.093);
  grid(data.groups[4].cells,.65,.82,3,.026,.09);grid(data.groups[5].cells,.88,.24,2,.043,.145);
  grid(data.groups[6].cells,.34,.91,4,.032,.08);p[99]=[.51,.91];return p;}
 root.RegionCore={phaseAt,frameAt,positions};if(typeof module!=='undefined')module.exports=root.RegionCore;
})(typeof globalThis!=='undefined'?globalThis:this);
