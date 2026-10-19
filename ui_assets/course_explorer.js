(()=>{'use strict';
const $=id=>document.getElementById(id),d=JSON.parse($('course-data').textContent),reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let selected=0,playing=false,elapsed=0,last=null;
const wrap=(id,content)=>`<g data-part="${id}" role="button" tabindex="0" aria-label="${d.parts.find(p=>p.id===id)?.name||id}">${content}</g>`;
const brain=`<svg viewBox="0 0 1050 380" role="img" aria-label="Simplified brain outer surface and separate medial cutaway"><text x="30" y="30">Outer surface · front ←</text><text x="650" y="30">Medial cutaway · simplified</text>
 ${wrap('frontal','<path class="part-fill" d="M245 67 C142 48 49 98 40 190 Q32 245 99 256 L228 214 L268 141 Z"/><text x="82" y="164">Frontal</text>')}
 ${wrap('parietal','<path class="part-fill" d="M245 67 C319 37 414 70 440 123 L382 207 L228 214 L268 141 Z"/><text x="296" y="131">Parietal</text>')}
 ${wrap('occipital','<path class="part-fill" d="M440 123 C520 151 516 241 446 262 L382 207 Z"/><text x="402" y="198">Occipital</text>')}
 ${wrap('temporal','<path class="part-fill" d="M99 256 L228 214 L382 207 L446 262 Q365 313 202 300 Q139 292 99 256"/><text x="225" y="270">Temporal</text>')}
 ${wrap('cerebellum','<path class="part-fill" d="M366 292 Q435 262 476 302 Q493 346 430 357 Q372 357 352 326 Z"/><path d="M380 307 Q430 291 464 314 M375 321 Q425 306 469 327 M390 336 Q428 325 457 341" fill="none" stroke="#77929a"/><text x="366" y="373" class="small">Cerebellum</text>')}
 ${wrap('brainstem','<path class="part-fill" d="M313 286 Q351 285 361 305 L357 366 L330 366 Z"/><text x="258" y="355" class="small">Brainstem</text>')}
 <path d="M645 238 C593 164 641 91 721 79 C827 41 959 93 982 171 Q1007 234 933 266 L899 300 L843 291 Q747 291 645 238" fill="#edf3ee" stroke="#688897" stroke-width="2"/>
 <path d="M696 181 Q764 112 863 148 Q909 163 927 196" fill="none" stroke="#57707e" stroke-width="12"/>
 ${wrap('thalamus','<ellipse class="part-fill" cx="802" cy="196" rx="41" ry="26"/><text x="802" y="199" text-anchor="middle" class="small">Thalamus</text>')}
 ${wrap('hippocampus','<path class="part-fill" d="M717 239 Q748 210 772 235 Q800 264 861 247 L870 261 Q798 286 753 255 Q738 242 726 253 Z"/><text x="736" y="312" class="small">Hippocampus</text><path d="M789 294 V269" stroke="#90b1bd"/>')}
 <text x="664" y="350" class="small">Projected positions are approximate; not a clinical atlas.</text></svg>`;
const neuron=`<svg viewBox="0 0 1050 350" role="img" aria-label="A schematic multipolar neuron with branched dendrites, cell body, axon and terminals">
 ${wrap('dendrites','<path class="part-line" d="M235 175 L155 100 L108 66 M155 100 L80 112 M178 124 L175 56 M230 175 L130 180 L57 146 M130 180 L59 211 M232 188 L156 258 L108 299 M156 258 L78 258"/><text x="53" y="33">Dendrites</text>')}
 ${wrap('soma','<path class="part-fill" d="M207 125 Q247 103 282 140 L312 175 L281 217 Q242 248 206 214 L188 177 Z"/><circle cx="245" cy="175" r="19" fill="#7c75aa"/><text x="210" y="279">Cell body</text>')}
 ${wrap('initial','<path class="part-line" d="M307 175 H368"/><text x="301" y="86" class="small">Initial segment</text><path d="M340 94 V153" stroke="#7696a6"/>')}
 ${wrap('axon','<path class="part-line" d="M368 175 H838"/><text x="554" y="279">Axon</text>')}
 ${wrap('myelin','<rect class="part-fill" x="390" y="150" width="88" height="50" rx="15"/><rect class="part-fill" x="496" y="150" width="88" height="50" rx="15"/><rect class="part-fill" x="602" y="150" width="88" height="50" rx="15"/><rect class="part-fill" x="708" y="150" width="88" height="50" rx="15"/><text x="490" y="91">Myelin</text><text x="584" y="223" class="small">Node</text><path d="M594 207 V183" stroke="#b4c9ce"/>')}
 ${wrap('terminals','<path class="part-line" d="M838 175 L895 109 L972 81 M895 109 L973 135 M838 175 L925 181 M838 175 L895 245 L976 271 M895 245 L974 219"/><circle class="part-fill" cx="978" cy="81" r="8"/><circle class="part-fill" cx="979" cy="135" r="8"/><circle class="part-fill" cx="932" cy="181" r="8"/><circle class="part-fill" cx="981" cy="271" r="8"/><circle class="part-fill" cx="980" cy="219" r="8"/><text x="853" y="320">Axon terminals</text>')}
 <circle id="signal-marker" cx="245" cy="175" r="9" fill="#ffe0a6" opacity="0"/></svg>`;
const voltage=`<svg viewBox="0 0 1050 350" role="img" aria-label="Illustrative action-potential waveform and sodium/potassium channel states"><text x="47" y="25">Membrane voltage · illustrative mV</text>
 <path d="M100 48 V302 H905" fill="none" stroke="#587480"/><path d="M100 260 H905" stroke="#35515c" stroke-dasharray="4 4"/>
 <text x="45" y="266">−70</text><text x="48" y="82">+30</text><text x="98" y="329" class="small">Sequence, not a measured time axis →</text>
 <path d="M111 260 H231 Q276 260 298 225 Q318 165 344 77 Q362 92 391 147 Q422 214 461 289 Q513 297 558 270 Q580 260 637 260 H902" fill="none" stroke="#78579b" stroke-width="4"/>
 <circle id="voltage-marker" cx="155" cy="260" r="9" fill="#126d70"/>
 <rect x="670" y="55" width="297" height="132" rx="13" fill="#edf3ee" stroke="#42616d"/><text x="690" y="82">Channel states · schematic</text>
 <text id="na-state" x="690" y="119" class="small">Na⁺ conductance</text><text id="k-state" x="690" y="151" class="small">K⁺ conductance</text>
 </svg>`;
$('title').textContent=d.title;$('scope').textContent=d.foot;$('drawing').innerHTML=d.kind==='brain'?brain:d.kind==='neuron'?neuron:voltage;
const buttons=[];
for(let i=0;i<d.parts.length;i++){const button=document.createElement('button');button.type='button';button.textContent=d.parts[i].name;button.addEventListener('click',()=>{playing=false;last=null;selected=i;draw();});$('choices').appendChild(button);buttons.push(button);}
for(const group of document.querySelectorAll('[data-part]')){const select=()=>{playing=false;selected=d.parts.findIndex(p=>p.id===group.getAttribute('data-part'));draw();};group.addEventListener('click',select);group.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select();}});}
const points=[[155,260],[344,77],[399,166],[476,291],[683,260]];
function draw(fraction=1){const p=d.parts[selected];$('part-name').textContent=p.name;$('part-detail').textContent=p.detail;
 buttons.forEach((button,i)=>button.setAttribute('aria-pressed',String(i===selected)));
 for(const group of document.querySelectorAll('[data-part]')){group.classList.toggle('active',group.getAttribute('data-part')===p.id);}
 if(d.kind==='voltage'){$('voltage-marker').setAttribute('cx',points[selected][0]);$('voltage-marker').setAttribute('cy',points[selected][1]);
  $('na-state').textContent=['Na⁺: low resting conductance','Na⁺: rapidly increasing','Na⁺: inactivated','Na⁺: recovering','Na⁺: ready for a later spike'][selected];
  $('k-state').textContent=['K⁺: resting permeability','K⁺: delayed activation','K⁺: elevated conductance','K⁺: remains elevated briefly','K⁺: toward resting conditions'][selected];}
 if(d.kind==='neuron'){const marker=$('signal-marker');marker.setAttribute('opacity',playing&&!reduced&&selected>=2?'1':'0');marker.setAttribute('cx',selected<3?335:selected===3?String(368+470*fraction):selected===4?'594':String(838+140*fraction));marker.setAttribute('cy',selected===5?String(175-94*fraction):'175');}
 $('position').textContent=(selected+1)+' / '+d.parts.length;$('play').textContent=playing?'Pause sequence':'Play sequence';
}
function stop(){playing=false;last=null;}
$('play').hidden=d.kind==='brain';$('play').addEventListener('click',()=>{if(playing)stop();else{selected=0;elapsed=0;last=null;playing=true;}draw(0);});
$('next').addEventListener('click',()=>{stop();selected=(selected+1)%d.parts.length;draw();});
$('previous').addEventListener('click',()=>{stop();selected=(selected+d.parts.length-1)%d.parts.length;draw();});
$('reset').addEventListener('click',()=>{stop();selected=0;draw();});
function tick(now){if(playing){if(last!==null)elapsed+=Math.min(80,now-last);last=now;selected=Math.min(d.parts.length-1,Math.floor(elapsed/2200));draw(reduced?1:(elapsed%2200)/2200);if(elapsed>=d.parts.length*2200){stop();draw();}}window.requestAnimationFrame(tick);}
draw();window.requestAnimationFrame(tick);
})();
