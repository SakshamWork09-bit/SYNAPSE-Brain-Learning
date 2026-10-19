(()=>{'use strict';
const $=id=>document.getElementById(id),d=JSON.parse($('guided-data').textContent),R=GuidedReplay;
const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let time=d.start,playing=false,last=null,selected=0;
$('seek').min=d.start;$('seek').max=d.stop;$('seek').step=d.dt;$('seek').value=d.start;
$('weight-bar').max=d.bounds[1];$('axis-start').textContent=d.start.toFixed(1)+' ms';$('axis-stop').textContent=d.stop.toFixed(1)+' ms';
$('run-title').textContent=d.label+' · pair '+d.pair+' of '+d.pairs;
const x=t=>35+830*(t-d.start)/(d.stop-d.start),NS='http://www.w3.org/2000/svg';
const markers=[['A spike',d.sourceSpike,'#85e0c0',0],['Arrival',d.arrival,'#ffd094',1],['B spike',d.targetSpike,'#c4b0ff',2]];
for(const [label,t,color,row] of markers){const g=document.createElementNS(NS,'g'),line=document.createElementNS(NS,'path'),text=document.createElementNS(NS,'text'),title=document.createElementNS(NS,'title');
 line.setAttribute('d',`M${x(t)} 12 V45`);line.setAttribute('stroke',color);line.setAttribute('stroke-width','3');
 title.textContent=label+' · '+t.toFixed(1)+' ms';line.appendChild(title);g.appendChild(line);
 // Legend rows avoid overlapping labels when arrival and spikes are close together.
 text.setAttribute('x',String(85+row*300));text.setAttribute('y','60');text.setAttribute('class','small');text.textContent=label+' '+t.toFixed(1)+' ms';g.appendChild(text);$('event-markers').appendChild(g);}
function draw(){const f=R.frame(d,time);
 $('clock').textContent=f.time.toFixed(1)+' ms · model time';$('seek').value=f.time;
 $('counts').textContent=f.counts.join(' / ');$('weight').textContent=f.weight.toFixed(6)+' nA';$('weight-bar').value=f.weight;
 $('phase').textContent=f.phase;$('cell-a').setAttribute('fill',f.active[0]?'#2d6256':'#1d3638');$('cell-b').setAttribute('fill',f.active[1]?'#645185':'#302c45');
 $('packet').setAttribute('opacity',f.travelling&&!reduced?'1':'0');$('packet').setAttribute('cx',String(210+480*f.progress));
 $('cursor').setAttribute('d',`M${x(f.time)} 5 V50`);
 $('play').textContent=playing?'Pause':'Play recording';$('step-event').disabled=f.time>=d.stop;
 $('inspect-a').setAttribute('aria-pressed',String(selected===0));$('inspect-b').setAttribute('aria-pressed',String(selected===1));
 $('inspect-value').textContent=(selected===0?'A':'B')+': '+f.voltage[selected].toFixed(3)+' mV · '+f.counts[selected]+' spike(s) recorded so far.';
}
function pause(){playing=false;last=null;}
$('play').addEventListener('click',()=>{if(playing)pause();else{if(time>=d.stop)time=d.start;playing=true;last=null;}draw();});
$('restart').addEventListener('click',()=>{time=d.start;pause();draw();});
$('step-event').addEventListener('click',()=>{time=R.nextEvent(d,time);pause();draw();});
$('seek').addEventListener('input',()=>{time=Number($('seek').value);pause();draw();});
for(const cell of [0,1])$(cell===0?'inspect-a':'inspect-b').addEventListener('click',()=>{selected=cell;draw();});
function tick(now){if(playing){if(last!==null)time+=Math.min(80,now-last)/8000*(d.stop-d.start)*Number($('speed').value);last=now;
 if(time>=d.stop){time=d.stop;pause();}draw();}window.requestAnimationFrame(tick);}
draw();window.requestAnimationFrame(tick);
})();
