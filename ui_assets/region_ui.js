(()=>{'use strict';
 const d=JSON.parse(document.getElementById('region-data').textContent),C=globalThis.RegionCore,$=id=>document.getElementById(id);
 let t=0,playing=false,last=null,cell=d.signal?.kind==='pattern'?0:18,manual=d.lesson,deep=['hippocampus','amygdala'].includes(d.lesson)?'hippocampus':d.lesson==='basal'?'deep':'medial',plateSignature='';
 const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
 const allNames=Object.keys(d.atlas),p=C.positions(d),group=n=>d.groups.find(g=>g.cells.includes(n));
 $('title').textContent=d.lessonTitle+' · structure, task, circuit';$('scope').textContent=d.scope;$('limits').textContent=d.limits;
 $('deepView').value=deep;$('deepView').addEventListener('change',e=>{deep=e.target.value;render();});
 $('recordingBadge').textContent=d.ready?'100 NEURONS / FROZEN PROBE':'EXPLORE THE ANATOMY';
 $('intro').textContent=d.ready?'Pause at any stage: the anatomical interpretation and the measured circuit share one playback clock. Choose a neuron to follow its voltage.':'Choose a structure below. Run the embedded experiment in this lesson to see anatomy and the calculated 100-cell circuit together.';
 function selectRegion(id){manual=id;const v=d.atlas[id].view;if(v!=='lateral'){deep=v;$('deepView').value=v;}render();}
 allNames.forEach(id=>{const b=document.createElement('button');b.type='button';b.textContent=d.atlas[id].name;b.addEventListener('click',()=>selectRegion(id));b.dataset.region=id;$('regionPills').appendChild(b);});
 function plate(view,target,regions){const a=d.plates[view],markers=allNames.filter(id=>d.atlas[id].view===view&&(regions.includes(id)||manual===id));
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox',`-8 -15 ${a.width+16} ${a.height+30}`);svg.setAttribute('role','img');svg.setAttribute('aria-label',a.title+'; highlighted: '+markers.map(id=>d.atlas[id].name).join(', '));
  const im=document.createElementNS(ns,'image');im.setAttribute('href',a.image);im.setAttribute('width',a.width);im.setAttribute('height',a.height);svg.appendChild(im);
  markers.forEach(id=>{const r=d.atlas[id],circle=document.createElementNS(ns,'circle');circle.setAttribute('cx',r.x*a.width);circle.setAttribute('cy',r.y*a.height);circle.setAttribute('r',r.r*a.width);circle.setAttribute('class','halo '+(regions.includes(id)?(id===d.lesson?'':'secondary'):'manual'));circle.setAttribute('role','button');circle.setAttribute('tabindex','0');circle.setAttribute('aria-label',r.name+' approximate location');circle.addEventListener('click',()=>selectRegion(id));circle.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectRegion(id);}});svg.appendChild(circle);
    const width=r.name.length*9+12,lx=Math.max(8,Math.min(a.width-width,r.x*a.width-width/2)),ly=Math.max(24,r.y*a.height-r.r*a.width-7),box=document.createElementNS(ns,'rect');box.setAttribute('x',lx-5);box.setAttribute('y',ly-18);box.setAttribute('width',width);box.setAttribute('height',24);box.setAttribute('rx',4);box.setAttribute('fill','#fffffff0');svg.appendChild(box);
    const label=document.createElementNS(ns,'text');label.setAttribute('x',lx);label.setAttribute('y',ly);label.setAttribute('stroke','none');label.textContent=r.name;svg.appendChild(label);});
  $(target).replaceChildren(svg);if(target==='surface'){$('surfaceTitle').textContent=a.title;$('surfaceNote').textContent=a.note;}else $('deepNote').textContent=a.title+'. '+a.note;
 }
 function sources(keys){$('phaseSources').replaceChildren();keys.forEach((key,i)=>{if(!d.sources[key])return;if(i)$('phaseSources').appendChild(document.createTextNode(' · '));const a=document.createElement('a');a.href=d.sources[key].url;a.textContent=d.sources[key].label;a.target='_blank';a.rel='noopener noreferrer';$('phaseSources').appendChild(a);});}
 function render(){const f=d.ready?C.frameAt(d,t,cell):null,s=f?.phase,regions=s?s.regions:[d.lesson];
  const signature=(s?.start??-1)+':'+deep+':'+manual;if(signature!==plateSignature){plate('lateral','surface',regions);plate(deep,'deep',regions);plateSignature=signature;
  $('phaseTitle').textContent=s?s.label+' · biological connections':'Locate '+d.atlas[manual].name;
  $('partners').textContent=s?'Structures in this explanation: '+regions.map(id=>d.atlas[id].name).join(' · '):'Select a structure, then follow its numbered lesson.';
  $('phaseWhy').textContent=s?s.why:d.coordination;sources(s?s.sources:[]);
  $('regionDetail').textContent='Selected structure: '+d.atlas[manual].name+'. '+(manual===d.lesson?d.cellular:'Open its numbered lesson in the course sidebar for its cellular mechanism and controlled task. The purple marker is your anatomical selection; it is not an activity claim.');
  Array.from($('regionPills').children).forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.region===manual)));
  }
  if(!d.ready)return;
  $('clock').textContent=t.toFixed(1)+' ms';$('time').value=t;$('play').textContent=playing?'Pause recording':'Play recording';
  if(d.signal.kind==='sequence'){const boxes=$('signalPreview').children[0]?.children||[];Array.from(boxes).forEach((box,i)=>{const start=d.signal.onset+i*d.signal.gap;box.classList.toggle('active',t>=start&&t<start+5);});}
  Array.from($('stageButtons').children).forEach((b,i)=>b.setAttribute('aria-current',d.stages[i]===s?'step':'false'));
  const preference=d.prediction===null?'undecided':(d.prediction===0?'A-leaning':'B-leaning');
  $('decision').textContent=!f.readoutReached?'Readout not reached':d.queryComparison?
   ((d.queryComparison.matchedExample===null?'No exact example match':'Input exactly Example '+(d.queryComparison.matchedExample+1))+' · neural preference: '+preference):
   (d.prediction===null?'Class readout: undecided':'Class readout: '+(d.prediction===0?'A':'B'));
  const g=group(cell),incoming=d.edges.filter(e=>e.target===cell).length,outgoing=d.edges.filter(e=>e.source===cell).length;
  $('neuron').value=cell;$('cellRole').textContent='N'+String(cell).padStart(2,'0')+' · '+g.name;$('cellExplain').textContent=g.detail;
  $('cellStats').textContent=f.cellSpikes+' spikes up to cursor · '+f.arrived+' arrivals received · '+incoming+' incoming / '+outgoing+' outgoing links';
  $('voltageLabel').textContent=f.voltage.toFixed(3)+' mV';$('cellCurrent').textContent='Synaptic current: '+f.current.toFixed(5)+' nA · External current: '+f.input.toFixed(3)+' nA. Values are interval-start currents; voltage is the state at the cursor.';
  drawNetwork();drawTrace();
 }
 function curve(ctx,a,b){const bend=Math.max(18,Math.abs(b[0]-a[0])*.44);ctx.moveTo(a[0],a[1]);ctx.bezierCurveTo(a[0]+bend,a[1],b[0]-bend,b[1],b[0],b[1]);}
 function drawNetwork(){const canvas=$('network'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height,pos=p.map(a=>[a[0]*w,a[1]*h]);ctx.clearRect(0,0,w,h);ctx.fillStyle='#fff';ctx.fillRect(0,0,w,h);
  const only=$('focusLinks').checked;d.edges.forEach(e=>{if(only&&e.source!==cell&&e.target!==cell)return;const focus=e.source===cell||e.target===cell;ctx.beginPath();curve(ctx,pos[e.source],pos[e.target]);ctx.strokeStyle=e.weight<0?(focus?'#b4496888':'#b4496816'):(focus?'#157e8655':'#97b6b515');ctx.lineWidth=focus?1.4:.65;ctx.stroke();});
  d.arrivals.forEach(a=>{const e=d.edges[a[1]],emission=a[0]-e.delay;if(t<emission||t>a[0]||(only&&e.source!==cell&&e.target!==cell))return;const q=(t-emission)/e.delay,from=pos[e.source],to=pos[e.target],bend=Math.max(18,Math.abs(to[0]-from[0])*.44),v=1-q;const x=v*v*v*from[0]+3*v*v*q*(from[0]+bend)+3*v*q*q*(to[0]-bend)+q*q*q*to[0],y=v*v*v*from[1]+3*v*v*q*from[1]+3*v*q*q*to[1]+q*q*q*to[1];ctx.beginPath();ctx.arc(x,y,2.8,0,Math.PI*2);ctx.fillStyle=e.weight<0?'#b44968':'#cb8a20';ctx.fill();});
  const row=C.frameAt(d,t,cell).index;pos.forEach((point,n)=>{const fired=d.spikes.some(s=>s[1]===n&&s[0]<=t&&t-s[0]<2.5),v=d.voltage[row][n],g=group(n);ctx.beginPath();ctx.arc(point[0],point[1],fired?8.5:6.2,0,Math.PI*2);ctx.fillStyle=fired?'#e6a72e':g.color;ctx.globalAlpha=.35+.65*Math.max(0,Math.min(1,(v+65)/15));ctx.fill();ctx.globalAlpha=1;ctx.strokeStyle=n===cell?'#203e48':'#ffffff';ctx.lineWidth=n===cell?3:1;ctx.stroke();});
  ctx.fillStyle='#3b5962';ctx.font='bold 13px system-ui';[['VISUAL INPUT',.035,.065],['SYMBOLS',.035,.81],['DELAYED HISTORY',.31,.065],['CONVERGENCE',.61,.065],['INHIBITION',.61,.76],['READOUT A / B',.85,.10],['CONTEXT',.33,.84],['CUE',.495,.84]].forEach(([label,x,y])=>ctx.fillText(label,x*w,y*h));
  ctx.font='12px system-ui';ctx.fillText('N'+String(cell).padStart(2,'0'),pos[cell][0]+10,pos[cell][1]-9);
 }
 function drawTrace(){const canvas=$('trace'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height,L=35,R=w-12,T=18,B=h-25;ctx.clearRect(0,0,w,h);ctx.fillStyle='#fff';ctx.fillRect(0,0,w,h);const x=time=>L+(R-L)*time/d.duration,y=v=>B-(B-T)*Math.max(0,Math.min(1,(v+65)/15));ctx.strokeStyle='#dae5e1';ctx.lineWidth=1;[-65,-60,-55,-50].forEach(v=>{ctx.beginPath();ctx.moveTo(L,y(v));ctx.lineTo(R,y(v));ctx.stroke();ctx.font='10px system-ui';ctx.fillStyle='#657b81';ctx.fillText(String(v),1,y(v)+3);});ctx.beginPath();d.time.forEach((time,i)=>{i?ctx.lineTo(x(time),y(d.voltage[i][cell])):ctx.moveTo(x(time),y(d.voltage[i][cell]));});ctx.strokeStyle=group(cell).color;ctx.lineWidth=2;ctx.stroke();d.spikes.filter(s=>s[1]===cell).forEach(s=>{ctx.fillStyle='#c27d22';ctx.fillRect(x(s[0])-2,T-6,4,6);});ctx.beginPath();ctx.moveTo(x(t),T);ctx.lineTo(x(t),B);ctx.strokeStyle='#b86b38';ctx.lineWidth=1.5;ctx.stroke();ctx.fillStyle='#657b81';ctx.font='11px system-ui';ctx.fillText('0 ms',L,h-6);ctx.fillText(d.duration+' ms',R-50,h-6);}
 if(d.ready){$('recordedPanel').hidden=false;$('time').max=d.duration;
  if(d.signal.kind==='pattern'){
   const board=document.createElement('div');board.className='pixel-board';board.setAttribute('aria-label','Recorded 3 by 3 input pattern');d.signal.content.forEach(v=>{const square=document.createElement('span');square.className=v?'lit':'unlit';square.textContent=v?'1':'0';board.appendChild(square);});$('signalPreview').appendChild(board);
   $('signalText').textContent='Nine OFF/ON pixel pairs receive the recorded drawing at '+d.signal.onset+' ms. The decoder receives no class label. Class A/B names refer to the teaching examples, not brain regions.';
  }else{const sequence=document.createElement('div');sequence.className='symbol-sequence';d.signal.content.forEach((symbol,i)=>{const box=document.createElement('span');box.textContent=symbol+' · '+(d.signal.onset+i*d.signal.gap)+' ms';sequence.appendChild(box);});$('signalPreview').appendChild(sequence);$('signalText').textContent='Symbols are current pulses to A/B/C source cells. The order and timing affect delayed activity. The decoder receives no expected response.';}
  if(d.queryComparison)$('signalText').textContent+=' '+d.queryComparison.summary+' '+d.queryComparison.basis;
  for(let n=0;n<100;n++){const o=document.createElement('option');o.value=n;o.textContent='N'+String(n).padStart(2,'0')+' · '+group(n).name;$('neuron').appendChild(o);}
  $('neuron').addEventListener('change',e=>{cell=Number(e.target.value);render();});$('focusLinks').addEventListener('change',render);
  d.stages.forEach((s,i)=>{const b=document.createElement('button');b.type='button';b.textContent=String(i+1).padStart(2,'0')+' · '+s.label;b.addEventListener('click',()=>{t=s.start;playing=false;const target=s.regions.find(id=>d.atlas[id].view!=='lateral');if(target){deep=d.atlas[target].view;$('deepView').value=deep;}render();});$('stageButtons').appendChild(b);});
  $('time').addEventListener('input',e=>{t=Number(e.target.value);playing=false;render();});$('play').addEventListener('click',()=>{if(t>=d.duration)t=0;playing=!playing;last=null;render();});$('restart').addEventListener('click',()=>{t=0;playing=false;render();});
  $('network').addEventListener('click',e=>{const r=$('network').getBoundingClientRect(),x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height;let best=-1,distance=Infinity;p.forEach((v,i)=>{const delta=(v[0]-x)**2+(v[1]-y)**2;if(delta<distance){distance=delta;best=i;}});if(distance<.0025){cell=best;render();}});
  $('network').addEventListener('keydown',e=>{if(['ArrowRight','ArrowDown','ArrowLeft','ArrowUp'].includes(e.key)){e.preventDefault();cell=(cell+(['ArrowRight','ArrowDown'].includes(e.key)?1:99))%100;render();}});
 }
 render();
 function tick(now){if(playing&&d.ready&&!document.hidden){if(last!==null)t=Math.min(d.duration,t+(now-last)*.015*Number($('speed').value));if(t>=d.duration)playing=false;render();}last=now;requestAnimationFrame(tick);}if(d.ready)requestAnimationFrame(tick);
 if(reduced)$('intro').textContent+=' Reduced-motion preference detected; playback starts paused.';
})();
