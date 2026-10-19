(function(){'use strict';
 const data=JSON.parse(document.getElementById('memory-data').textContent),$=id=>document.getElementById(id);
 const canvas=$('input'),net=$('network'),ic=canvas.getContext('2d'),nc=net.getContext('2d');
 let time=0,playing=data.ready&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches,last=null,dirty=true,selected=null;
 $('identity').textContent='Seed '+data.seed+' · '+data.presentations+' teaching presentations';$('seek').max=String(data.duration);
 $('recipe').textContent=!data.ready?'No query yet':data.kind==='pattern'?'3 × 3 pixel pattern':data.signal.content.join('');
 $('timing').textContent=data.ready?'Read at '+data.readoutTime+' ms · '+data.duration+' ms recorded':'Run a frozen query to record the response.';
 const xy=i=>[data.positions[i][0]*760,data.positions[i][1]*540];
 function drawInput(f){const c=ic;c.clearRect(0,0,480,480);c.font='14px system-ui';c.textAlign='center';
  if(!data.ready){c.fillStyle='#526c75';c.fillText('Create a signal and run a frozen query.',240,220);return;}
  if(data.kind==='pattern'){for(let i=0;i<9;i++){const x=75+(i%3)*110,y=65+Math.floor(i/3)*110,on=data.signal.content[i]===1,live=time>=data.signal.onset_ms&&time<data.signal.onset_ms+5;c.fillStyle=on?(live?'#126d70':'#4e9e90'):'#e7eeea';c.fillRect(x,y,100,100);c.strokeStyle='#b9cfc4';c.strokeRect(x,y,100,100);}}
  else{const n=data.signal.content.length;c.strokeStyle='#afc7ba';c.lineWidth=2;c.beginPath();c.moveTo(40,260);c.lineTo(440,260);c.stroke();for(let i=0;i<n;i++){const x=50+i*380/Math.max(1,n-1),start=data.signal.onset_ms+i*data.signal.gap_ms,seen=time>=start;c.fillStyle=seen?'#c68a31':'#d6e4dc';c.beginPath();c.arc(x,220,23,0,Math.PI*2);c.fill();c.fillStyle=seen?'#203e48':'#3e6066';c.font='20px system-ui';c.fillText(data.signal.content[i],x,227);c.fillStyle='#526c75';c.font='11px system-ui';c.fillText(start+' ms',x,287);}
   c.fillStyle='#126d70';c.fillRect(40+400*time/data.duration,310,3,25);c.fillStyle='#526c75';c.fillText('Recorded neural time',240,370);}}
 function drawNetwork(f){const c=nc;c.clearRect(0,0,760,540);data.edges.forEach((e,i)=>{const a=xy(e.source),b=xy(e.target);c.strokeStyle=e.plastic?'#75a6a12e':'#aaa0dd33';c.lineWidth=.5+Math.min(1.2,data.weights[i]*40);c.beginPath();c.moveTo(...a);c.lineTo(...b);c.stroke();});
  for(const p of f.packets){const e=data.edges[p.index],a=xy(e.source),b=xy(e.target);c.fillStyle='#b57723';c.beginPath();c.arc(a[0]+(b[0]-a[0])*p.progress,a[1]+(b[1]-a[1])*p.progress,2.5,0,Math.PI*2);c.fill();}
  for(let i=0;i<50;i++){const p=xy(i),g=data.groups.find(g=>g.ids.includes(i));c.fillStyle=f.active.has(i)?'#c88b2a':g.color;c.globalAlpha=.4+.6*Math.max(0,Math.min(1,(f.voltage[i]+65)/15));c.beginPath();c.arc(...p,f.active.has(i)?8:5,0,Math.PI*2);c.fill();c.globalAlpha=1;if(selected===i){c.strokeStyle='#203e48';c.beginPath();c.arc(...p,11,0,Math.PI*2);c.stroke();}}
  c.fillStyle='#526c75';c.font='10px system-ui';c.textAlign='left';for(const g of data.groups){const p=xy(g.ids[0]);c.fillText(g.name,p[0]-8,p[1]-18);}}
 function render(){const f=MemoryReplay.frame(data,time);if(window.updateSynapseBiology)window.updateSynapseBiology(time);drawInput(f);drawNetwork(f);$('clock').textContent=time.toFixed(1)+' ms';$('phase').textContent=f.phase;$('seek').value=String(time);$('play').textContent=playing?'Pause':'Play';$('play').disabled=!data.ready;$('restart').disabled=!data.ready;
  $('response').textContent=!f.revealed?'Waiting':f.prediction===null?'No clear response':'Response '+(f.prediction===0?'A':'B');
  $('scores').textContent=f.revealed?'A '+f.scores[0].toFixed(3)+' mV · B '+f.scores[1].toFixed(3)+' mV · margin '+data.margin.toFixed(3)+' mV':'Response appears only at readout.';
  $('neuron').textContent=selected===null?'Click a cell to inspect its voltage.':'N'+selected+' · '+f.voltage[selected].toFixed(3)+' mV · '+f.counts[selected]+' spikes so far';dirty=false;}
 $('play').addEventListener('click',()=>{if(time>=data.duration)time=0;playing=!playing;last=null;dirty=true;});$('restart').addEventListener('click',()=>{time=0;playing=true;last=null;dirty=true;});$('seek').addEventListener('input',()=>{time=Number($('seek').value);playing=false;dirty=true;});$('speed').addEventListener('change',()=>{last=null;});
 net.addEventListener('click',e=>{const r=net.getBoundingClientRect(),x=(e.clientX-r.left)*760/r.width,y=(e.clientY-r.top)*540/r.height;let best=18;selected=null;data.positions.forEach((_,i)=>{const p=xy(i),d=Math.hypot(x-p[0],y-p[1]);if(d<best){best=d;selected=i;}});dirty=true;});
 net.addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();selected=((selected===null?0:selected)+(e.key==='ArrowRight'?1:49))%50;dirty=true;}});
 function tick(now){if(playing){if(last!==null)time=Math.min(data.duration,time+(now-last)*data.duration/6000*Number($('speed').value));if(time>=data.duration)playing=false;dirty=true;}last=now;if(dirty)render();window.requestAnimationFrame(tick);}render();window.requestAnimationFrame(tick);
})();
