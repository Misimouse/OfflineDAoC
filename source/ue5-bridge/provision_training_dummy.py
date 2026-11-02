"""Real GM inventory round trip via the normal launcher and game protocol.
Never edits the database, gives money, or destroys/drops items.
"""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time,math,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'Reports/training_staff_fx_pets';O.mkdir(exist_ok=True);LIVE=R/'Reports/live'
DOTNET=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe')
snapshot={};buffer=b'';session='';serial=0;sock=None;process=None
result={'real_server':True,'character':'BridgeFighter','steps':[],'errors':[],'normal_logout':False,'transactions_started':False}
class CommerceUnavailable(Exception):pass
baseline={};purchased=None;source_slot=-1;equip_slot=-1
def write():(O/'server_verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
def pump(duration=.15):
 global buffer,session,snapshot
 end=time.monotonic()+duration
 while time.monotonic()<end:
  try:data=sock.recv(1048576)
  except socket.timeout:continue
  if not data:raise RuntimeError('Bridge closed')
  buffer+=data
  while b'\n' in buffer:
   line,buffer=buffer.split(b'\n',1);value=json.loads(line)
   if value.get('type')=='hello':session=value['session']
   if value.get('type')=='snapshot':snapshot=value
def wait(predicate,label,timeout=18):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  pump()
  if predicate():return
 raise RuntimeError('Timeout: '+label+'; '+snapshot.get('inventory',{}).get('feedback',''))
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(values,type='command',session=session,id='inventory-probe:'+str(serial),action=action))+'\n').encode())

try:
 with (O/'dummy_session.log').open('w') as log:
  process=subprocess.Popen([DOTNET,str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeCaster','--session-only'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  end=time.monotonic()+90
  while time.monotonic()<end:
   try:sock=socket.create_connection(('127.0.0.1',19727),timeout=.2);break
   except OSError:time.sleep(.2)
  if sock is None:raise RuntimeError('Bridge not ready')
  sock.settimeout(.1);wait(lambda:session and snapshot.get('in_game') and snapshot.get('inventory',{}).get('ready'),'Original session ready',80);pump(2)
  local=lambda:next(e for e in snapshot['entities'] if e['id']=='player:local')
  original_pos=list(local()['position_m']);original_items=snapshot['inventory']['items'];original_target=snapshot.get('interaction',{}).get('target',{}).get('id','')
  result={'passed':False,'real_server':True,'character':'BridgeCaster','errors':[]}
  provision=O/'dummy_provision.json'
  previous=json.loads(provision.read_text()) if provision.exists() else {}
  found=[e for e in snapshot['entities'] if e.get('name')=='Ardee Training Dummy']
  assert len(found)<=1,'Multiple pre-existing training dummies; no new creation'
  def jump(point):
   send('chat',text='/jump to %d %d %d 200'%(round(point[0]*40)+35*8192,round(point[2]*40)+51*8192,round(point[1]*40)))
   wait(lambda:math.dist(local()['position_m'],point)<1,'GM transfer')
  placement=json.loads((O/'dummy_placement.json.result.json').read_text(encoding='utf-8-sig'));assert placement['passed']
  jump(placement['position_m']);pump(1)
  if found:entity=found[0]['id'];result['reused_existing']=True
  else:
   assert not previous.get('created_oid'),'Prior dummy creation recorded; refusing duplicate'
   before=max((e['id'] for e in snapshot.get('chat',{}).get('entries',[])),default=0)
   send('chat',text='/mob create DOL.GS.GameTrainingDummy 3')
   created=lambda:[e for e in snapshot.get('chat',{}).get('entries',[]) if e['id']>before and e['text'].startswith('Mob created: OID=')]
   wait(lambda:bool(created()),'Exact original NPC creation response')
   oid=int(created()[-1]['text'].split('OID=')[1]);entity='npc:'+str(oid)
   provision.write_text(json.dumps({'created_oid':oid,'position_m':placement['position_m'],'configured':False},indent=2))
  wait(lambda:any(e['id']==entity for e in snapshot['entities']),'Created dummy appears')
  send('target',entity_id=entity);wait(lambda:snapshot.get('interaction',{}).get('target',{}).get('id')==entity,'Exact dummy target')
  for command in ['/mob flags 0','/mob model 2009','/mob level 1','/mob realm 0','/mob name Ardee Training Dummy']:
   send('chat',text=command);pump(.7)
  wait(lambda:any(e['id']==entity and e.get('model_id')==2009 and e.get('name')=='Ardee Training Dummy' for e in snapshot['entities']),'Original dummy configured')
  result.update(dummy_id=entity,model=2009,position_m=placement['position_m'],level=1)
  provision.write_text(json.dumps(dict(created_oid=int(entity.split(':')[1]),position_m=placement['position_m'],configured=True),indent=2))
  result['inventory_unchanged']=snapshot['inventory']['items']==original_items
  result['passed']=result['inventory_unchanged']
except Exception:
 if 'result' not in globals():result={}
 result.setdefault('errors',[]).append(traceback.format_exc())
finally:
 if sock:
  try:
   if 'original_pos' in globals():jump(original_pos);result['original_position_restored']=math.dist(local()['position_m'],original_pos)<1
   if 'original_target' in globals():send('target',entity_id=original_target);pump(.3)
   send('logout');(LIVE/'logout.request').write_text('logout')
  except Exception:result.setdefault('errors',[]).append('Cleanup: '+traceback.format_exc())
 if process:
  try:process.wait(timeout=100)
  except subprocess.TimeoutExpired:result.setdefault('errors',[]).append('Normal logout still pending; process left running')
 if sock:sock.close()
 final=json.loads((LIVE/'godot_session.json').read_text(encoding='utf-8-sig'))
 result['normal_logout']=not final.get('playing',True)
 result['passed']=bool(result.get('passed') and result.get('normal_logout') and result.get('original_position_restored') and not result.get('errors'))
 (O/'dummy_server_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
 if not result['passed']:raise SystemExit(1)
