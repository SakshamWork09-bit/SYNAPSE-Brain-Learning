(function() {
  'use strict';
  const data=JSON.parse(document.getElementById('replay-data').textContent);
  const probe=data.kind==='probe';
  const R=window.SynapseReplay;
  const $=id=>document.getElementById(id);
  $('manualLegend').style.display=probe?'flex':'none';
  const canvas=$('network'),ctx=canvas.getContext('2d');
  const nodes=R.positions(data),curves=data.edges.map(e=>R.curve(nodes,e));
  const reducedMotion=window.matchMedia?window.matchMedia('(prefers-reduced-motion: reduce)').matches:false;
  let time=0,playing=data.ready&&!reducedMotion,selected=null,speed=1,previous=null,width=900,height=350;
  const changedEver=data.ready?data.finalWeights.map((w,i)=>w-data.initialWeights[i]):data.initialWeights.map(()=>0);
  $('identity').textContent=probe?`Frozen probe · ${data.branch}`:
    data.ready?`Recorded experience ${data.trial} · seed ${data.seed}`:`50 neurons · 690 links · seed ${data.seed}`;
  $('scope').textContent=data.ready?
    `Recorded simulation ${data.absoluteStart.toFixed(1)}–${(data.absoluteStart+data.duration).toFixed(1)} ms. Playback 1× stretches this window to 6 seconds. No new learning is run by this display. ${data.arrivals.length} actual arrivals in this window.`:
    'This is the existing circuit at its current boundary, not a running demonstration. Press Step 1 above to calculate an experience.';
  $('time').max=data.duration;
  if(probe) {
    $('inputLabel').textContent='01 · MANUAL INPUT';$('actionLabel').textContent='02 · TRANSMISSION CONTROLS';
    $('feedbackLabel').textContent='03 · MEASURED RESPONSE';
    $('pad0').textContent=data.manualGains.filter(g=>g===0).length+' blocked links';
    $('pad1').textContent=data.manualGains.filter(g=>g!==1).length+' manual gains';
    document.querySelector('h1').textContent='Intervene and observe.';
    document.querySelector('.intro').textContent='Frozen neural response to a declared pulse and temporary transmission controls.';
    document.querySelector('details').textContent='This is a frozen probe, not a learning trial. There is no action decoder, success score or reward update. Manual gains scale future arrivals without editing learned weights. Grey dashed links are blocked and carry no recorded packets. Existing currents still decay. Replay controls only inspect the recording; the continuing session was preserved.';
  }
  if(data.course){
    document.querySelector('h1').textContent=data.course.title;
    document.querySelector('.intro').textContent=data.course.intro;
    if(!data.ready)$('scope').textContent='Existing wiring, with no recorded activity yet. Use Launch a signal above to calculate a response.';
    document.querySelector('details').textContent=data.course.explanation||'These columns show engineered circuit roles, not anatomical areas. Flashes and travelling markers come from calculated spikes and arrivals. Click a neuron to inspect it or use arrow keys. Replay changes only the display. In a frozen pulse experiment there is no choice or reward update. A temporary gain changes transmission, not learned weights.';
  }
  if(!data.ready){$('play').disabled=true;$('restart').disabled=true;$('time').disabled=true;}
  const pos=(p)=>({x:p.x*width,y:p.y*height});
  function resize() {
    const rect=canvas.getBoundingClientRect();width=rect.width;height=rect.height;
    const ratio=Math.min(window.devicePixelRatio||1,2);
    canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);
    ctx.setTransform(ratio,0,0,ratio,0,0);draw();
  }
  function path(c) {
    const a=pos(c.a),b=pos(c.b),m=pos(c.c);
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.quadraticCurveTo(m.x,m.y,b.x,b.y);
  }
  function arrow(c,color) {
    const p=pos(R.point(c,.80)),q=pos(R.point(c,.76));
    const angle=Math.atan2(p.y-q.y,p.x-q.x),size=3;
    ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(p.x,p.y);
    ctx.lineTo(p.x-size*Math.cos(angle-.5),p.y-size*Math.sin(angle-.5));
    ctx.lineTo(p.x-size*Math.cos(angle+.5),p.y-size*Math.sin(angle+.5));ctx.closePath();ctx.fill();
  }
  function edgeVisible(edge) {
    return !$('focus').checked || selected===null || edge.source===selected || edge.target===selected;
  }
  function draw() {
    const frame=R.frameAt(data,time);
    if(window.updateSynapseBiology)window.updateSynapseBiology(time);
    ctx.clearRect(0,0,width,height);
    ['SENSORY','ASSOCIATION','INHIBITION','ACTION'].forEach((text,i)=>{
      ctx.fillStyle='#526c75';ctx.font='10px system-ui';ctx.textAlign='center';
      ctx.fillText(text,(.09+i*.27)*width,20);
    });
    for(let i=0;i<data.edges.length;i++) {
      const edge=data.edges[i];if(!edgeVisible(edge))continue;
      const w=frame.weights[i],incident=selected!==null&&(edge.source===selected||edge.target===selected);
      const alpha=incident ? .65 : .10;
      const gain=data.manualGains?data.manualGains[i]:1;
      const color=gain===0?'rgba(130,143,155,.23)':gain!==1?'rgba(229,188,107,.40)':
        w<0?`rgba(222,149,105,${alpha})`:`rgba(18,109,112,${alpha})`;
      ctx.setLineDash(gain===0?[3,4]:[]);
      path(curves[i]);ctx.strokeStyle=color;ctx.lineWidth=Math.min(2.2,.35+Math.abs(w)*22);ctx.stroke();
      ctx.setLineDash([]);if(gain!==0)arrow(curves[i],color);
      if(frame.feedback&&time<data.feedbackTime+12&&Math.abs(changedEver[i])>1e-12) {
        path(curves[i]);ctx.strokeStyle=changedEver[i]>0?'rgba(120,235,183,.55)':'rgba(239,130,171,.55)';
        ctx.lineWidth=1.25;ctx.stroke();
      }
    }
    for(const packet of frame.packets) {
      if(!edgeVisible(data.edges[packet.edge]))continue;
      const c=curves[packet.edge],p=pos(R.point(c,packet.progress));
      path(c);ctx.strokeStyle=packet.weight<0?'rgba(245,174,117,.55)':'rgba(18,109,112,.55)';
      ctx.lineWidth=1;ctx.stroke();
      ctx.beginPath();ctx.arc(p.x,p.y,2.1,0,Math.PI*2);
      ctx.fillStyle=packet.weight<0?'#b44b66':'#b77b24';ctx.fill();
    }
    data.groups.forEach((group,gi)=>{
      const ids=group.neurons;
      const anchor=nodes[ids[0]];
      ctx.fillStyle='#526c75';ctx.font='9px system-ui';ctx.textAlign='center';
      ctx.fillText(gi<6?(gi%2?'B':'A'):(gi%2?'1':'0'),anchor.x*width,anchor.y*height-13);
    });
    nodes.forEach((node,id)=>{
      const p=pos(node),flash=frame.flashes.has(id);
      const level=Math.max(0,Math.min(1,(frame.voltage[id]-data.rest)/(data.threshold-data.rest)));
      const radius=flash?7:4.2+1.2*level;
      if(flash){ctx.beginPath();ctx.arc(p.x,p.y,11,0,Math.PI*2);ctx.fillStyle='rgba(198,138,49,.20)';ctx.fill();}
      ctx.globalAlpha=flash?1:.55+.45*level;
      ctx.beginPath();ctx.arc(p.x,p.y,radius,0,Math.PI*2);ctx.fillStyle=flash?'#c88b2a':node.color;ctx.fill();ctx.globalAlpha=1;
      if(id===selected){ctx.beginPath();ctx.arc(p.x,p.y,10,0,Math.PI*2);ctx.strokeStyle='#203e48';ctx.lineWidth=1.5;ctx.stroke();}
    });
    $('clock').textContent=`${time.toFixed(1)} ms`;
    $('time').value=time;
    $('phase').textContent=frame.phase;
    $('play').textContent=playing?'Pause replay':'Play replay';
    if(probe) {
      const pulse=data.stimulus,active=time>=pulse.start&&time<pulse.stop&&pulse.amplitude!==0;
      $('cue').textContent=pulse.amplitude===0?'No added pulse':`${pulse.amplitude.toFixed(2)} nA`;
      $('inputText').textContent=`N${pulse.neurons.join(', N')} · pulse interval ${pulse.start}–${pulse.stop} ms.`;
      $('inputCard').classList.toggle('active',active);
      $('actionText').textContent='Manual transmission gains are fixed throughout this probe. Learned weights stay frozen.';
      const spikes=data.spikes.filter(([t])=>t<=time),cells=new Set(spikes.map(e=>e[1]));
      $('outcome').textContent=`${spikes.length} spikes so far`;
      $('feedbackText').textContent=`${cells.size} active cells so far. No task action or reward is generated.`;
      $('change').textContent='MANUAL INTERVENTION · learned weights unchanged';
    } else {
    const ready=data.ready;
    $('cue').textContent=ready?`Signal ${data.cue===0?'A':'B'}`:'Waiting';
    $('inputText').textContent=ready?(time<5?'A 0.8 nA pulse drives the selected sensory group.':'The input pulse ended at 5 ms; subsequent activity is calculated.'):'Press Step 1 in the app to calculate an experience.';
    $('inputCard').classList.toggle('active',ready&&time<5);
    $('actionCard').classList.toggle('active',frame.decision&&!frame.feedback);
    $('feedbackCard').classList.toggle('active',frame.feedback);
    for(let i=0;i<2;i++)$('pad'+i).classList.toggle('chosen',frame.action===i);
    $('actionText').textContent=frame.decision?
      `Chose ${data.action} at 25 ms · neural scores ${data.scores[0].toFixed(2)} / ${data.scores[1].toFixed(2)} mV · P(0/1) ${(100*data.probabilities[0]).toFixed(0)} / ${(100*data.probabilities[1]).toFixed(0)}%.`:
      'The circuit has not selected its action yet. Feedback is still unavailable.';
    $('outcome').textContent=frame.feedback?(frame.reward===1?'Successful choice':'Unsuccessful choice'):'Not yet';
    let feedbackText='Feedback arrives at 35 ms, after the choice.';
    if(frame.feedback) {
      const mode=data.mode==='learning_disabled'?'Learning disabled.':data.mode==='random_feedback'?'Uncorrelated-feedback control.':'Outcome-based learning.';
      feedbackText=`Actual reward ${data.reward}; delivered feedback ${data.feedback}. ${mode}`;
    }
    $('feedbackText').textContent=feedbackText;
    const stronger=frame.changed.filter(e=>e.delta>0).length,weaker=frame.changed.length-stronger;
    $('change').textContent=frame.feedback?`${stronger} links strengthened · ${weaker} weakened · no links created`:'Weights have not received this outcome yet';
    }
    if(selected!==null) {
      const incoming=data.edges.filter(e=>e.target===selected).length;
      const outgoing=data.edges.filter(e=>e.source===selected).length;
      const count=data.spikes.filter(([t,n])=>n===selected&&t<=time).length;
      $('detail').textContent=`N${selected} · ${data.groups[nodes[selected].group].name} · ${frame.voltage[selected].toFixed(2)} mV · ${count} spikes so far · ${incoming} in / ${outgoing} out`;
    } else $('detail').textContent='All existing connections are visible automatically. Click a neuron for optional detail.';
    return frame;
  }
  function nearest(event) {
    const rect=canvas.getBoundingClientRect(),x=event.clientX-rect.left,y=event.clientY-rect.top;
    let best=null,distance=14;
    nodes.forEach((p,i)=>{const d=Math.hypot(p.x*width-x,p.y*height-y);if(d<distance){best=i;distance=d;}});
    return {id:best,x,y};
  }
  canvas.addEventListener('click',event=>{selected=nearest(event).id;draw();});
  canvas.addEventListener('mousemove',event=>{
    const p=nearest(event),tooltip=$('tooltip');
    tooltip.hidden=p.id===null;
    if(p.id!==null) {
      const f=R.frameAt(data,time);
      tooltip.textContent=`N${p.id} · ${data.groups[nodes[p.id].group].name}\n${f.voltage[p.id].toFixed(2)} mV\nClick for connection detail`;
      tooltip.style.left=Math.min(width-210,p.x+12)+'px';tooltip.style.top=Math.max(0,p.y-55)+'px';
    }
  });
  canvas.addEventListener('mouseleave',()=>{$('tooltip').hidden=true;});
  canvas.addEventListener('keydown',event=>{
    if(event.key==='ArrowRight'||event.key==='ArrowLeft') {
      selected=(selected===null?0:(selected+(event.key==='ArrowRight'?1:49))%50);draw();event.preventDefault();
    }
  });
  $('play').addEventListener('click',()=>{if(time>=data.duration)time=0;playing=!playing;previous=null;draw();});
  $('restart').addEventListener('click',()=>{time=0;playing=true;previous=null;draw();});
  $('speed').addEventListener('change',()=>{speed=Number($('speed').value);});
  $('time').addEventListener('input',()=>{time=Number($('time').value);playing=false;draw();});
  $('focus').addEventListener('change',draw);
  $('clear').addEventListener('click',()=>{selected=null;$('focus').checked=false;draw();});
  function animate(now) {
    let changed=false;
    if(playing&&previous!==null) {
      // Never skip to the end after a background-tab pause.
      time=Math.min(data.duration,time+Math.min(now-previous,100)*data.duration/6000*speed);
      if(time>=data.duration)playing=false;
      changed=true;
    }
    previous=now;if(changed)draw();window.requestAnimationFrame(animate);
  }
  new ResizeObserver(resize).observe(canvas);
  resize();window.requestAnimationFrame(animate);
})();
