"""Validated experiential lesson state and actual 100-cell learning requests.

Most activities are transparent browser-side teaching models or a human task.
Recognition/association use this server's real spiking encoder/readout; inference
receives the query pixels, never an expected class or a destination label.
"""

import copy
import json
import math
from pathlib import Path

from .memory_lab import Task, Signal
from .region_model import RegionModel, probe, controlled_teaching

ASSETS = Path(__file__).resolve().parents[1] / 'ui_assets' / 'experiences'
ACTIVITIES = json.loads((ASSETS / 'activities.json').read_text(encoding='utf-8'))
NEURAL_IDS = ('temporal','hippocampus')


def _bounded_json(value, depth=0):
    if depth>8: raise ValueError('Experiment state is too deeply nested.')
    if value is None or type(value) is bool: return
    if type(value) in (int,float):
        if not math.isfinite(value) or abs(value)>1e15: raise ValueError('Invalid numeric state.')
    elif type(value) is str:
        if len(value)>400: raise ValueError('Experiment text is too long.')
    elif type(value) is list:
        if len(value)>256: raise ValueError('Too much experiment history.')
        for item in value: _bounded_json(item,depth+1)
    elif type(value) is dict:
        if len(value)>64 or any(type(k) is not str or len(k)>80 or k in ('__proto__','constructor','prototype') for k in value):
            raise ValueError('Invalid experiment fields.')
        for item in value.values(): _bounded_json(item,depth+1)
    else: raise ValueError('Experiment state must be JSON.')


def _pixels(values):
    if type(values) is not list or len(values)!=9 or any(type(x) is not int or x not in (0,1) for x in values):
        raise ValueError('Each drawing needs nine ON/OFF pixels.')
    return tuple(values)


def _number(value, low=-1e15, high=1e15):
    return type(value) in (int,float) and math.isfinite(value) and low<=value<=high


def _rows(data, field='history'):
    rows=data.get(field)
    if type(rows) is not list or len(rows)>120 or any(type(r) is not dict for r in rows):
        raise ValueError('Invalid recorded experiment history.')
    if data.get('last') is not None and type(data['last']) is not dict: raise ValueError('Invalid last observation.')


def validate_state(value, id):
    if id not in ACTIVITIES or type(value) is not dict: raise ValueError('Unknown experiment.')
    _bounded_json(value)
    if len(json.dumps(value,allow_nan=False).encode())>64*1024: raise ValueError('Experiment state exceeds 64 KiB.')
    required={'format','id','seq','step','seed','settings','data','message'}
    if set(value)!=required or value['format']!='synapse-experience-v1' or value['id']!=id:
        raise ValueError('Wrong experiment state format.')
    if type(value['seq']) is not int or not 0<=value['seq']<=10**9 or value['step'] not in ('intro','play','why'):
        raise ValueError('Invalid experiment step.')
    if type(value['seed']) is not int or not 0<=value['seed']<2**32: raise ValueError('Invalid experiment seed.')
    if value['message'] is not None and type(value['message']) is not str: raise ValueError('Invalid experiment message.')
    settings=value['settings'];specs=ACTIVITIES[id]['settings']
    if type(settings) is not dict or set(settings)!=set(specs): raise ValueError('Experiment settings do not match this lesson.')
    for key,spec in specs.items():
        v=settings[key]
        if 'choices' in spec:
            if type(v) is not str or v not in spec['choices']: raise ValueError(f'Invalid setting: {key}.')
        elif type(v) not in (int,float) or not math.isfinite(v) or not spec['min']<=v<=spec['max']:
            raise ValueError(f'Invalid setting: {key}.')
    data=value['data']
    if type(data) is not dict: raise ValueError('Invalid experiment data.')
    if id in NEURAL_IDS:
        if set(data) != {'examples','query','trained','response','presentations','history'}:
            raise ValueError('Invalid learning experiment data.')
        if type(data['examples']) is not list or len(data['examples'])!=2: raise ValueError('Edit two independent examples.')
        for drawing in data['examples']: _pixels(drawing)
        _pixels(data['query'])
        if type(data['presentations']) is not int or not 0<=data['presentations']<=16384 or type(data['history']) is not list or len(data['history'])>120:
            raise ValueError('Invalid learning history.')
        _rows(data)
        trained=data['trained'];response=data['response']
        if trained is not None:
            if type(trained) is not dict or set(trained)!={'examples','places'} or type(trained['examples']) is not list or len(trained['examples'])!=2:
                raise ValueError('Invalid taught examples.')
            pair=[_pixels(p) for p in trained['examples']]
            if pair[0]==pair[1]: raise ValueError('Taught examples must differ.')
            if trained['places'] is not None and trained['places'] not in (['Window','Door'],['Door','Window']):
                raise ValueError('Invalid taught places.')
        if response is not None:
            if type(response) is not dict or set(response)!={'prediction','scores','margin','query','weight_hash','places'}:
                raise ValueError('Invalid saved neural response.')
            if response['prediction'] is not None and (type(response['prediction']) is not int or response['prediction'] not in (0,1)):
                raise ValueError('Invalid saved neural answer.')
            if type(response['scores']) is not list or len(response['scores'])!=2 or any(not _number(v,0,100) for v in response['scores']):
                raise ValueError('Invalid response voltages.')
            if not _number(response['margin']) or abs(response['margin']-(response['scores'][0]-response['scores'][1]))>1e-8:
                raise ValueError('Invalid voltage difference.')
            _pixels(response['query'])
            fingerprint=response['weight_hash']
            if type(fingerprint) is not str or len(fingerprint)!=64 or any(c not in '0123456789abcdef' for c in fingerprint):
                raise ValueError('Invalid response weight identity.')
            if response['places']!=(['Window','Door'] if id=='hippocampus' else None): raise ValueError('Invalid output meanings.')
        for row in data['history']:
            if any(type(row.get(k)) is not int for k in ('presentations','correct','total','disabled')) or not 0<=row['correct']<=row['total']==16 or not 0<=row['disabled']<=16:
                raise ValueError('Invalid teaching comparison.')
    elif id=='occipital': _pixels(data.get('pixels'))
    elif id=='pfc':
        if data.get('phase') not in ('ready','cue','wait','answer','done') or type(data.get('round')) is not int: raise ValueError('Invalid rule task.')
        if data['phase']!='ready':
            cards=[data.get('target'),*(data.get('options') if type(data.get('options')) is list else [])]
            if len(cards)!=3 or any(type(c) is not dict or set(c)!={'colour','shape'} or any(type(v) is not int or v not in (0,1) for v in c.values()) for c in cards):
                raise ValueError('Invalid rule-task cards.')
            if data.get('rule') not in ('colour','shape') or type(data.get('correctSide')) is not int or data['correctSide'] not in (0,1):
                raise ValueError('Invalid kept rule.')
            if data['phase']=='wait' and not _number(data.get('readyAt'),0): raise ValueError('Invalid waiting time.')
    elif id=='parietal':
        if type(data.get('spotlight')) is not int or not 0<=data['spotlight']<16: raise ValueError('Choose one spatial location.')
    elif id in ('basal','amygdala'):
        vals=data.get('values')
        if type(vals) is not list or len(vals)!=2 or any(type(v) not in (int,float) or not 0<=v<=1 for v in vals): raise ValueError('Invalid learned values.')
        _rows(data)
    elif id=='cerebellum':
        if type(data.get('compensation')) not in (int,float) or abs(data['compensation'])>200: raise ValueError('Invalid reach compensation.')
        _rows(data)
    elif id=='hypothalamus':
        if type(data.get('internal')) not in (int,float) or not 0<=data['internal']<=100: raise ValueError('Invalid internal state.')
        if not _number(data.get('integral'),-6,6) or not _number(data.get('time'),0): raise ValueError('Invalid feedback state.')
        _rows(data)
    elif id=='brainstem':
        if type(data.get('v')) not in (int,float) or not 0<=data['v']<1 or type(data.get('brake')) not in (int,float) or data['brake']<0: raise ValueError('Invalid rhythm state.')
        if not _number(data.get('time'),0) or type(data.get('pulses')) is not list or len(data['pulses'])>120 or any(not _number(t,0,data['time']) for t in data['pulses']):
            raise ValueError('Invalid pulse times.')
        _rows(data)
    elif id in ('motor','thalamus'):
        if type(data.get('runs')) is not int or data['runs']<0: raise ValueError('Invalid exploration count.')
    return copy.deepcopy(value)


class ExperienceSession:
    def __init__(self):
        self.states={};self.models={};self.sequences={};self.replies={};self.recordings={};self.epoch=0

    def handle(self, value, id):
        """Consume each browser operation once. Invalid/stale messages cannot teach."""
        if type(value) is not dict or value.get('format')!='synapse-experience-message-v1' or value.get('id')!=id:
            return False
        if type(value.get('epoch')) is not int or value['epoch']!=self.epoch: return False
        seq=value.get('sequence')
        if type(seq) is not int or not 1<=seq<=10**9 or seq<=self.sequences.get(id,0): return False
        state=validate_state(value.get('state'),id)
        operation=value.get('operation')
        if operation not in ('sync','teach','probe','reset'): raise ValueError('Unknown experiment operation.')
        if operation!='sync' and id not in NEURAL_IDS: raise ValueError('This activity has no learned neural readout.')
        if id in NEURAL_IDS:
            # Pixels/settings are editable. Calculated answers and teaching evidence
            # come from the server, including when a stale draft arrives after teaching.
            prior=self.states.get(id,{}).get('data',{})
            for key,default in (('trained',None),('response',None),('presentations',0),('history',[])):
                state['data'][key]=copy.deepcopy(prior.get(key,default))
        # Everything below is computed on a copy before committing the model.
        reply={'sequence':seq,'operation':operation,'error':None}
        if operation!='sync':
            try:
                model=self.models.get(id,RegionModel()).clone()
                if operation=='reset':
                    model=RegionModel()
                    state['data'].update(trained=None,response=None,presentations=0,history=[])
                    self.recordings.pop(id,None)
                else:
                    data=state['data'];examples=tuple(_pixels(v) for v in data['examples'])
                    query=Signal('pattern',_pixels(data['query']),12.)
                    if operation=='teach':
                        if examples[0]==examples[1]: raise ValueError('Make the two teaching drawings different.')
                        places=[state['settings']['placeA'],state['settings']['placeB']] if id=='hippocampus' else None
                        if places and places[0]==places[1]: raise ValueError('Use different places for this two-place experiment.')
                        # Output channels keep fixed physical meanings. Swapping places
                        # reverses the teachers, not just the text after the answer.
                        ordered=examples[::-1] if places and places[0]=='Door' else examples
                        task=Task('pattern',ordered)  # rejects identical drawings before alteration
                        previous=probe(model,query,record=True)
                        model,evidence=controlled_teaching(model,task,epochs=32)
                        data['trained']={'examples':[list(p) for p in examples],'places':places}
                        data['history']=(data['history']+[{'presentations':model.presentations,'correct':evidence['chosen']['correct'],
                            'total':evidence['chosen']['total'],'disabled':evidence['disabled']['correct']}])[-120:]
                    else: previous=None
                    result=probe(model,query,record=True)
                    data['response']={'prediction':result['prediction'],'scores':result['scores_mV'],'margin':result['margin_mV'],
                                      'query':list(query.content),'weight_hash':result['weight_sha256'],
                                      'places':['Window','Door'] if id=='hippocampus' else None}
                    data['presentations']=model.presentations
                    self.recordings[id]={'before':previous,'after':result}
                self.models[id]=model
                state['message']=None
            except (ValueError,FloatingPointError) as exc:
                reply['error']=str(exc)
                state['message']=str(exc)[:400]
        self.states[id]=state;self.sequences[id]=seq;self.replies[id]=reply
        return True

    def json_bytes(self):
        value={'format':'synapse-experiences-bundle-v1','states':self.states,
               'models':{id:json.loads(model.json_bytes()) for id,model in self.models.items()}}
        data=json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2).encode()
        self.from_bytes(data)
        return data

    @classmethod
    def from_bytes(cls,data):
        if type(data) is not bytes or len(data)>2*1024*1024: raise ValueError('Experiment bundle must be JSON within 2 MiB.')
        try:
            value=json.loads(data)
            if set(value)!={'format','states','models'} or value['format']!='synapse-experiences-bundle-v1' or type(value['states']) is not dict or type(value['models']) is not dict:
                raise ValueError('Wrong experiment bundle format.')
            if len(value['states'])>12 or any(k not in NEURAL_IDS for k in value['models']): raise ValueError('Unknown saved experiment.')
            obj=cls()
            obj.states={id:validate_state(state,id) for id,state in value['states'].items()}
            obj.models={id:RegionModel.from_bytes(json.dumps(model,allow_nan=False).encode()) for id,model in value['models'].items()}
            if any(id not in obj.states for id in obj.models): raise ValueError('A saved model needs its activity state.')
            for id,state in obj.states.items():
                if id not in NEURAL_IDS: continue
                d=state['data'];model=obj.models.get(id)
                if d['presentations']!=(model.presentations if model else 0): raise ValueError('Teaching count and saved weights disagree.')
                if d['response'] and (model is None or d['response']['weight_hash']!=model.fingerprint()):
                    raise ValueError('Saved response and weights disagree.')
                if d['trained'] and model is None: raise ValueError('Taught examples need their model weights.')
            return obj
        except (KeyError,TypeError,ValueError,OverflowError) as exc:
            raise ValueError(f'Experiments were not restored: {exc}') from exc
