(function(){'use strict';
  const data=JSON.parse(document.getElementById('arena-data').textContent),$=id=>document.getElementById(id);
  const names=['Up','Right','Down','Left'],sensorNames=['Goal ↑','Goal →','Goal ↓','Goal ←','Unsafe ↑','Unsafe →','Unsafe ↓','Unsafe ←'];
  const board=$('board'),net=$('network'),bc=board.getContext('2d'),nc=net.getContext('2d');
  let time=0,playing=data.ready&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches,last=null,selected=null,dirty=true;
  $('identity').textContent=data.ready?'Seed '+data.seed+' · move '+(data.row.move+1)+(data.row.frozen?' · frozen':' · '+data.mode):'No move recorded';
  const chips=sensorNames.map(name=>{const x=document.createElement('span');x.className='sensor';x.textContent=name;$('sensors').appendChild(x);return x;});
  const same=(a,b)=>a&&b&&a[0]===b[0]&&a[1]===b[1];
  function drawBoard(f){
    const c=bc,w=480,size=80,pad=40;c.clearRect(0,0,w,w);
    for(let r=0;r<5;r++)for(let col=0;col<5;col++){
      const wall=data.world.walls.some(p=>same(p,[r,col])),hazard=data.world.hazards.some(p=>same(p,[r,col]));
      c.fillStyle=wall?'#71827c':'#edf3ee';c.strokeStyle='#c3d5cb';c.lineWidth=1;c.fillRect(pad+col*size+3,pad+r*size+3,size-6,size-6);c.strokeRect(pad+col*size+3,pad+r*size+3,size-6,size-6);
      if(hazard){c.strokeStyle='#a6384e';c.lineWidth=3;c.beginPath();c.moveTo(pad+col*size+29,pad+r*size+29);c.lineTo(pad+col*size+51,pad+r*size+51);c.moveTo(pad+col*size+51,pad+r*size+29);c.lineTo(pad+col*size+29,pad+r*size+51);c.stroke();}
    }
    c.strokeStyle='#126d7066';c.lineWidth=3;c.beginPath();f.trail.forEach((p,i)=>{const x=pad+p[1]*size+40,y=pad+p[0]*size+40;i?c.lineTo(x,y):c.moveTo(x,y);});c.stroke();
    if(data.goal){const x=pad+data.goal[1]*size+40,y=pad+data.goal[0]*size+40;c.fillStyle='#b77b24';c.beginPath();for(let k=0;k<8;k++){const a=k*Math.PI/4,rad=k%2?8:19;k?c.lineTo(x+Math.cos(a)*rad,y+Math.sin(a)*rad):c.moveTo(x+Math.cos(a)*rad,y+Math.sin(a)*rad);}c.closePath();c.fill();}
    if(f.position){const x=pad+f.position[1]*size+40,y=pad+f.position[0]*size+40;c.fillStyle='#126d70';c.beginPath();c.arc(x,y,17,0,Math.PI*2);c.fill();c.strokeStyle='#d9fff6';c.lineWidth=2;c.stroke();if(f.decision){const d=[[-1,0],[0,1],[1,0],[0,-1]][f.action];c.beginPath();c.moveTo(x,y);c.lineTo(x+d[1]*28,y+d[0]*28);c.stroke();}}
    c.fillStyle='#526c75';c.font='11px system-ui';c.textAlign='center';for(let i=0;i<5;i++){c.fillText(String(i+1),pad+i*size+40,24);c.fillText(String(i+1),20,pad+i*size+44);}
  }
  const xy=i=>[data.positions[i][0]*760,data.positions[i][1]*540];
  function drawNetwork(f){
    const c=nc;c.clearRect(0,0,760,540);
    data.edges.forEach((e,i)=>{const a=xy(e.source),b=xy(e.target);c.strokeStyle=f.weights[i]<0?(data.n>50?'#e59b7210':'#e59b7225'):(data.n>50?'#709ca20a':'#709ca21c');c.lineWidth=.4+Math.min(.9,Math.abs(f.weights[i])*12);c.beginPath();c.moveTo(...a);c.lineTo(...b);c.stroke();});
    for(const p of f.packets){const e=data.edges[p.index],a=xy(e.source),b=xy(e.target);c.fillStyle=p.weight<0?'#efa679':'#147e81';c.beginPath();c.arc(a[0]+(b[0]-a[0])*p.progress,a[1]+(b[1]-a[1])*p.progress,2.6,0,Math.PI*2);c.fill();}
    for(let i=0;i<data.n;i++){const [x,y]=xy(i),g=data.groups.find(g=>g.ids.includes(i));c.fillStyle=f.active.has(i)?'#c88b2a':g.color;c.globalAlpha=.45+.55*Math.max(0,Math.min(1,(f.voltage[i]-data.rest)/(data.threshold-data.rest)));c.beginPath();c.arc(x,y,f.active.has(i)?8:5.5,0,Math.PI*2);c.fill();c.globalAlpha=1;if(selected===i){c.strokeStyle='#203e48';c.lineWidth=1.5;c.beginPath();c.arc(x,y,11,0,Math.PI*2);c.stroke();}}
    c.font='10px system-ui';c.fillStyle='#526c75';c.textAlign='left';data.groups.forEach((g,i)=>{const p=xy(g.ids[0]);c.fillText(g.name,p[0]-8,p[1]-18);});
  }
  function render(){const f=ArenaReplay.frame(data,time);if(window.updateSynapseBiology)window.updateSynapseBiology(time);drawBoard(f);drawNetwork(f);$('clock').textContent=time.toFixed(1)+' ms';$('phase').textContent=f.phase;$('seek').value=String(time);$('play').textContent=playing?'Pause':'Play';$('play').disabled=!data.ready;$('restart').disabled=!data.ready;
    chips.forEach((x,i)=>x.className='sensor'+(data.ready&&data.row.observation[i]?' on':''));
    $('action').textContent=f.decision?names[f.action]:'Waiting';
    $('scores').textContent=f.decision?'Selected probability '+(100*data.row.probabilities[f.action]).toFixed(1)+'% · '+(data.row.frozen?'greedy frozen readout':'softmax + 20% exploration'):'Read from action-cell voltages before feedback.';
    $('outcome').textContent=f.feedback?(data.row.success?'Goal reached':data.row.hazard?'Hazard':data.row.collision?'Collision':data.row.terminal?'Step limit':'Moved '+names[f.action].toLowerCase()):'Waiting';
    $('feedback').textContent=f.feedback?'Environment '+data.row.reward.toFixed(2)+' · delivered '+data.row.delivered_feedback.toFixed(2)+' · Δw '+data.row.update_l2_nA.toFixed(4)+' nA':'Movement and outcome are revealed together at 35 ms.';
    $('neuron').textContent=selected===null?'Click a neuron to inspect its calculated voltage.':'N'+selected+' · '+f.voltage[selected].toFixed(2)+' mV · '+f.counts[selected]+' spikes so far';dirty=false;
  }
  $('play').addEventListener('click',()=>{if(time>=100)time=0;playing=!playing;last=null;dirty=true;});
  $('restart').addEventListener('click',()=>{time=0;playing=true;last=null;dirty=true;});
  $('seek').addEventListener('input',()=>{time=Number($('seek').value);playing=false;dirty=true;});
  $('speed').addEventListener('change',()=>{last=null;});
  net.addEventListener('click',e=>{const rect=net.getBoundingClientRect(),x=(e.clientX-rect.left)*760/rect.width,y=(e.clientY-rect.top)*540/rect.height;let best=18;selected=null;data.positions.forEach((_,i)=>{const p=xy(i),d=Math.hypot(x-p[0],y-p[1]);if(d<best){selected=i;best=d;}});dirty=true;});
  net.addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();selected=((selected===null?0:selected)+(e.key==='ArrowRight'?1:data.n-1))%data.n;dirty=true;}});
  function tick(now){if(playing){if(last!==null)time=Math.min(100,time+(now-last)/60*Number($('speed').value));if(time>=100)playing=false;dirty=true;}last=now;if(dirty)render();window.requestAnimationFrame(tick);}
  render();window.requestAnimationFrame(tick);
})();
