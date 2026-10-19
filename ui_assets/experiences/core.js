/* Pure, inspectable teaching-model mechanics. No DOM and no biological activity claims. */
(function(root){'use strict';
 const IDS=['pfc','occipital','cerebellum','temporal','parietal','hippocampus','basal','motor','thalamus','amygdala','hypothalamus','brainstem'];
 const A=[1,0,0,1,0,0,1,1,1],B=[1,1,1,0,1,0,0,1,0];
 const clone=o=>JSON.parse(JSON.stringify(o)),clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
 function finite(n){if(typeof n!=='number'||!Number.isFinite(n))throw Error('Use a finite number.');return n;}
 function pixels(v){if(!Array.isArray(v)||v.length!==9||v.some(x=>x!==0&&x!==1))throw Error('Draw nine ON/OFF pixels.');return v.slice();}
 function initialData(id){switch(id){
  case'pfc':return {phase:'ready',round:0,target:null,options:[],choice:null,correct:null};
  case'occipital':return {pixels:[0,1,1,0,1,1,0,1,1]};
  case'cerebellum':return {compensation:0,history:[],last:null};
  case'temporal':case'hippocampus':return {examples:[A.slice(),B.slice()],query:A.slice(),trained:null,response:null,presentations:0,history:[]};
  case'parietal':return {spotlight:5};
  case'basal':return {values:[.5,.5],history:[],last:null};
  case'motor':case'thalamus':return {runs:0};
  case'amygdala':return {values:[0,0],history:[],last:null};
  case'hypothalamus':return {internal:50,integral:0,time:0,history:[{time:0,value:50,control:0}],last:null};
  case'brainstem':return {v:0,brake:0,time:0,pulses:[],history:[{time:0,value:0,brake:0}],last:null};
  default:throw Error('Unknown activity.');}}
 function create(id,config){if(!IDS.includes(id))throw Error('Unknown activity.');return {format:'synapse-experience-v1',id,seq:0,step:'intro',seed:7,settings:Object.fromEntries(Object.entries(config.settings).map(([k,v])=>[k,v.value])),data:initialData(id),message:null};}
 function random(s){s.seed=(Math.imul(s.seed,1664525)+1013904223)>>>0;return s.seed/4294967296;}
 function remember(list,row){list.push(row);if(list.length>120)list.splice(0,list.length-120);}
 function setting(state,key,value,config){const spec=config.settings[key];if(!spec)throw Error('Unknown setting.');
  if(spec.choices){if(!spec.choices.includes(value))throw Error('Choose one of the available settings.');}
  else {finite(value);if(value<spec.min||value>spec.max)throw Error('Setting is outside its range.');}
  const s=clone(state);s.settings[key]=value;s.seq++;return s;}
 function vision(s){const p=pixels(s.data.pixels),noise=[-.35,.4,-.15,.2,-.45,.3,.1,-.2,.4],q=p.map((v,i)=>clamp(.5+(v-.5)*s.settings.contrast+noise[i]*s.settings.noise,0,1));
  const v=[-1,0,1,-2,0,2,-1,0,1],h=[-1,-2,-1,0,0,0,1,2,1],dot=k=>Math.abs(q.reduce((a,x,i)=>a+x*k[i],0)/4);
  return {input:q,vertical:dot(v),horizontal:dot(h)};}
 function spatial(s){const input=Array.from({length:16},(_,i)=>i===10?.65:i===1?1:.1+(i%3)*.025),row=Math.floor(s.data.spotlight/4),col=s.data.spotlight%4;
  const weights=input.map((_,i)=>1+s.settings.gain*Math.exp(-((Math.floor(i/4)-row)**2+(i%4-col)**2)/(2*s.settings.width**2))),evidence=input.map((v,i)=>v*weights[i]);
  return {input,weights,evidence,winner:evidence.indexOf(Math.max(...evidence))};}
 function motor(s){const rad=s.settings.angle*Math.PI/180,preferred=Array.from({length:8},(_,i)=>i*45),rates=preferred.map(a=>String(a)===s.settings.suppressed?0:s.settings.strength*Math.max(0,Math.cos(rad-a*Math.PI/180)));
  const x=rates.reduce((a,r,i)=>a+r*Math.cos(preferred[i]*Math.PI/180),0)/2,y=rates.reduce((a,r,i)=>a+r*Math.sin(preferred[i]*Math.PI/180),0)/2,magnitude=Math.hypot(x,y);
  return {preferred,rates,x,y,magnitude,angle:magnitude<1e-9?null:(Math.atan2(y,x)*180/Math.PI+360)%360};}
 function relay(s){return {input:[s.settings.inputA,s.settings.inputB],output:[Math.max(0,s.settings.inputA*s.settings.gainA-s.settings.inhibition),Math.max(0,s.settings.inputB*s.settings.gainB-s.settings.inhibition)]};}
 function act(state,name,arg={}){const s=clone(state),d=s.data,k=s.settings;s.seq++;s.message=null;
  if(name==='begin'){s.step='play';return s;}if(name==='why'){s.step='why';return s;}if(name==='play'){s.step='play';return s;}
  if(name==='reset'){s.data=initialData(s.id);s.step='play';return s;}
  switch(s.id){
   case'pfc':
    if(name==='start'){const colour=Math.floor(random(s)*2),shape=Math.floor(random(s)*2),correctSide=Math.floor(random(s)*2);d.round++;d.target={colour,shape};d.rule=k.rule;d.correctSide=correctSide;d.options=[{colour:1-colour,shape:1-shape},{colour:1-colour,shape:1-shape}];d.options[correctSide]={colour,shape};d.options[1-correctSide][k.rule==='colour'?'shape':'colour']=k.rule==='colour'?shape:colour;d.phase='cue';d.choice=null;d.correct=null;}
    else if(name==='hide'){if(d.phase!=='cue')throw Error('Start a new round first.');d.phase='wait';d.readyAt=finite(arg.now)+k.delay*1000;}
    else if(name==='ready'){if(d.phase==='wait')d.phase='answer';}
    else if(name==='choose'){if(d.phase!=='answer')throw Error('Wait for the response cards.');if(arg.index!==0&&arg.index!==1)throw Error('Choose a card.');d.choice=arg.index;d.correct=arg.index===d.correctSide;d.phase='done';}
    else throw Error('Unknown rule-task action.');break;
   case'occipital':
    if(name==='pixel'){const i=arg.index;if(!Number.isInteger(i)||i<0||i>8)throw Error('Invalid pixel.');d.pixels[i]=1-d.pixels[i];}
    else if(name==='preset'){d.pixels=arg.name==='vertical'?[0,1,1,0,1,1,0,1,1]:arg.name==='horizontal'?[0,0,0,1,1,1,1,1,1]:arg.name==='uniform'?Array(9).fill(1):Array(9).fill(0);}
    else throw Error('Unknown visual action.');break;
   case'cerebellum':{
    if(name==='removeShift'){s.settings.shift=0;return s;}if(name!=='reach')throw Error('Unknown reach action.');const count=arg.count??1;if(!Number.isInteger(count)||count<1||count>20)throw Error('Use 1–20 reaches.');
    for(let i=0;i<count;i++){const before=d.compensation,error=k.shift-before;d.compensation=before+k.learning*error;const row={trial:(d.last?.trial??0)+1,shift:k.shift,before,error,after:d.compensation};d.last=row;remember(d.history,row);}break;}
   case'temporal':case'hippocampus':
    if(name==='pixel'){const i=arg.index;if(!Number.isInteger(i)||i<0||i>8)throw Error('Invalid pixel.');const board=arg.board==='a'?d.examples[0]:arg.board==='b'?d.examples[1]:arg.board==='q'?d.query:null;if(!board)throw Error('Choose an editable board.');board[i]=1-board[i];}
    else if(name==='copy'){if(arg.index!==0&&arg.index!==1)throw Error('Choose an example.');d.query=pixels(d.examples[arg.index]);}
    else if(name==='swapPlaces'){const old=k.placeA;k.placeA=k.placeB;k.placeB=old;}
    else throw Error('Unknown example action.');break;
   case'parietal':if(name!=='spotlight'||!Number.isInteger(arg.index)||arg.index<0||arg.index>15)throw Error('Choose a location.');d.spotlight=arg.index;break;
   case'basal':{
    if(name!=='choose'&&name!=='auto')throw Error('Choose an action.');const count=name==='auto'?(arg.count??8):1;if(!Number.isInteger(count)||count<1||count>20)throw Error('Use 1–20 trials.');
    for(let i=0;i<count;i++){const action=name==='choose'?arg.index:random(s)<.2?Math.floor(random(s)*2):d.values[0]===d.values[1]?Math.floor(random(s)*2):Number(d.values[1]>d.values[0]);if(action!==0&&action!==1)throw Error('Choose Action 1 or 2.');const before=d.values[action],outcome=action===0?k.rewardA:k.rewardB,error=outcome-before;d.values[action]+=k.learning*error;d.last={trial:(d.last?.trial??0)+1,action,before,outcome,error,after:d.values[action]};remember(d.history,{...d.last,values:d.values.slice()});}break;}
   case'motor':if(name!=='move')throw Error('Unknown movement action.');d.runs++;d.last=motor(s);break;
   case'thalamus':if(name!=='send')throw Error('Unknown relay action.');d.runs++;d.last=relay(s);break;
   case'amygdala':{
    if(name!=='pair'&&name!=='unpair'&&name!=='probe')throw Error('Choose a cue presentation.');const cue=arg.index;if(cue!==0&&cue!==1)throw Error('Choose Cue 1 or 2.');const count=name==='probe'?1:(arg.count??1);if(!Number.isInteger(count)||count<1||count>20)throw Error('Use 1–20 presentations.');
    for(let i=0;i<count;i++){const before=d.values[cue],outcome=name==='probe'?null:name==='unpair'?0:cue===0?k.outcomeA:k.outcomeB,error=outcome===null?0:outcome-before;if(outcome!==null)d.values[cue]+=k.learning*error;d.last={trial:(d.last?.trial??0)+1,cue,before,outcome,error,after:d.values[cue],updated:outcome!==null};remember(d.history,d.last);}break;}
   case'hypothalamus':{
    if(name!=='advance')throw Error('Unknown feedback action.');const count=arg.count??20;if(!Number.isInteger(count)||count<1||count>80)throw Error('Use 1–80 steps.');for(let i=0;i<count;i++){const error=k.target-d.internal;if(k.feedback==='on')d.integral=clamp(d.integral+.03*error,-6,6);const control=k.feedback==='on'?clamp(k.gain*error+d.integral,-8,8):0;d.internal=clamp(d.internal+.08*(k.outside-d.internal)+control,0,100);d.time++;d.last={time:d.time,value:d.internal,control};remember(d.history,d.last);}break;}
   case'brainstem':{
    if(name!=='advance')throw Error('Unknown rhythm action.');const count=arg.count??120;if(!Number.isInteger(count)||count<1||count>240)throw Error('Use 1–240 integration steps.');for(let i=0;i<count;i++){d.brake*=Math.exp(-k.recovery*.1);d.v=Math.max(0,d.v+.1*(k.drive-.1*d.v-k.inhibition*d.brake));d.time=Number((d.time+.1).toFixed(4));let pulse=false;if(d.v>=1){d.v=0;d.brake+=1.2;remember(d.pulses,d.time);pulse=true;}remember(d.history,{time:d.time,value:d.v,brake:d.brake,pulse});}d.last={time:d.time,pulses:d.pulses.length};break;}
   default:throw Error('Unknown activity.');
  }return s;
 }
 function receive(state,reply){const s=clone(state);if(!['temporal','hippocampus'].includes(s.id))throw Error('This activity has no neural readout.');if(reply.error){s.message=reply.error;return s;}
  const d=s.data;if(reply.operation==='reset'){s.data=initialData(s.id);return s;}
  d.presentations=reply.presentations;d.response=clone(reply.response);if(reply.operation==='teach'){d.trained={examples:clone(reply.examples),places:clone(reply.places??null)};remember(d.history,{presentations:reply.presentations,correct:reply.correct,total:reply.total,disabled:reply.disabled});}s.seq++;return s;
 }
 const api={IDS,create,initialData,setting,act,vision,spatial,motor,relay,receive,pixels,clone};root.ExperienceCore=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
