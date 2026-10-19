(()=>{'use strict';
const $=id=>document.getElementById(id);let lag=10,revision=-1,sequence=0,dragging=false,disabled=false,dragStartLag=10;
function send(type,data={}){window.parent.postMessage({isStreamlitMessage:true,type,...data},'*');}
function draw(){const marker=$('b-marker');marker.setAttribute('transform',`translate(${450+8.75*lag} 0)`);marker.setAttribute('aria-valuenow',String(lag));marker.setAttribute('aria-valuetext',lag===0?'Same time as arrival':Math.abs(lag)+' milliseconds '+(lag>0?'after arrival':'before arrival'));
 $('b-label').textContent='B · '+(lag>0?'+':'')+lag+' ms';$('status').textContent=lag===0?'B fires at the arrival time.':`B fires ${Math.abs(lag)} ms ${lag>0?'after':'before'} A’s signal arrives.`;}
function commit(){if(disabled)return;send('streamlit:setComponentValue',{value:{lag_ms:lag,revision,sequence:++sequence},dataType:'json'});}
function move(event){const svg=$('axis'),matrix=svg.getScreenCTM();if(!matrix)return;const point=svg.createSVGPoint();point.x=event.clientX;point.y=event.clientY;const x=point.matrixTransform(matrix.inverse()).x;lag=Math.max(-40,Math.min(40,Math.round((x-450)/8.75)));draw();}
$('b-marker').addEventListener('pointerdown',event=>{if(disabled)return;dragStartLag=lag;dragging=true;$('b-marker').setPointerCapture(event.pointerId);move(event);event.preventDefault();});
$('b-marker').addEventListener('pointermove',event=>{if(dragging)move(event);});
$('b-marker').addEventListener('pointerup',event=>{if(!dragging)return;move(event);dragging=false;commit();});
$('b-marker').addEventListener('pointercancel',()=>{dragging=false;lag=dragStartLag;draw();});
$('b-marker').addEventListener('keydown',event=>{if(disabled)return;const keys={ArrowLeft:lag-1,ArrowRight:lag+1,Home:-40,End:40};if(!(event.key in keys))return;event.preventDefault();lag=Math.max(-40,Math.min(40,keys[event.key]));draw();commit();});
function resize(){send('streamlit:setFrameHeight',{height:Math.max(230,document.body.scrollHeight+4)});}
window.addEventListener('message',event=>{if(event.source!==window.parent||event.data?.type!=='streamlit:render')return;
 const args=event.data.args;if(!args||!Number.isInteger(args.lag_ms)||!Number.isInteger(args.revision))return;
 lag=Math.max(-40,Math.min(40,args.lag_ms));revision=args.revision;disabled=Boolean(event.data.disabled);document.body.setAttribute('aria-disabled',String(disabled));draw();
 resize();});
window.addEventListener('resize',resize);
send('streamlit:componentReady',{apiVersion:1});draw();resize();
})();
