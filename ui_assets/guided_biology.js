(()=>{'use strict';
const $=id=>document.getElementById(id),reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const headings=['An electrical signal reaches the terminal.','Transmitter carries the message across the gap.','Receptors change the receiving cell’s response.'];
const copies=['An action potential reaches the presynaptic terminal. Voltage-gated calcium channels can open, coupling an electrical event to transmitter release. The green overlay is an explanatory marker, not a moving substance.','Calcium entry can promote vesicle fusion and neurotransmitter release. Transmitter diffuses across the cleft and can bind postsynaptic receptors. Reuptake, diffusion and breakdown help terminate signalling, depending on the transmitter and synapse.','Receptors can directly gate ion channels or act through intracellular signalling. Their effect depends on receptor type, ion gradients and membrane state. Whether the receiving cell fires also depends on its other inputs and current state.'];
let stage=0,playing=false,elapsed=0,last=null;
function draw(fraction=1){
 $('bio-heading').textContent=headings[stage];$('bio-copy').textContent=copies[stage];
 for(let i=0;i<3;i++)$('bio-'+i).setAttribute('aria-pressed',String(i===stage));
 $('signal').setAttribute('cx','470');
 $('signal').setAttribute('opacity',stage===0?'1':'0');
 $('vesicle').setAttribute('opacity',stage===1?'1':'.15');
 $('molecules').setAttribute('opacity',stage>=1?'1':'0');
 for(let i=0;i<3;i++){$('m'+i).setAttribute('cx',String(400+15*i));}
 $('response').setAttribute('opacity',stage===2?'1':'0');
 $('receptors').setAttribute('stroke',stage===2?'#b67c2b':'#78579b');
 $('bio-play').textContent=playing?'Pause':'Play illustration';
}
function stop(){playing=false;last=null;draw();}
for(let i=0;i<3;i++)$('bio-'+i).addEventListener('click',()=>{stage=i;elapsed=0;stop();});
$('bio-reset').addEventListener('click',()=>{stage=0;elapsed=0;stop();});
$('bio-play').addEventListener('click',()=>{if(playing)stop();else{playing=true;stage=0;elapsed=0;last=null;draw(0);}});
function tick(now){if(playing){if(last!==null)elapsed+=Math.min(80,now-last);last=now;
 const next=Math.min(2,Math.floor(elapsed/2400));stage=next;draw(reduced?1:Math.min(1,(elapsed%2400)/1800));
 if(elapsed>=7200){playing=false;last=null;draw();}}
 window.requestAnimationFrame(tick);}
draw();window.requestAnimationFrame(tick);
})();
