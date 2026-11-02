import sys as _bridge_sys
from pathlib import Path as _BridgePath
_bridge_sys.path.insert(0,str(_BridgePath(__file__).resolve().parents[1]))
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3,math
class Peer:
 def __init__(self,port):
  deadline=time.monotonic()+30
  while time.monotonic()<deadline:
   try:self.sock=socket.create_connection(('127.0.0.1',port),timeout=.2);break
   except OSError:time.sleep(.2)
  else:raise RuntimeError('QA bridge unavailable')
  self.sock.settimeout(.03);self.buffer=b'';self.snapshot={};self.session='';self.serial=0;self.trace=[]
 def send(self,action,**values):
  self.serial+=1;self.sock.sendall((json.dumps(dict(type='command',session=self.session,id='qa-group:'+str(self.serial),action=action,**values))+'\n').encode())
 def pump(self):
  try:chunk=self.sock.recv(1048576)
  except socket.timeout:return
  if not chunk:raise RuntimeError('QA bridge closed')
  self.buffer+=chunk
  while b'\n' in self.buffer:
   line,self.buffer=self.buffer.split(b'\n',1);value=json.loads(line)
   if value.get('type')=='hello':self.session=value['session']
   if value.get('type')=='snapshot':self.snapshot=value;self.trace.append(value)
 def party(self):return self.snapshot.get('classic_ui',{}).get('party',{})
peers=[];clients=[];handles=[];server=None;relay=None
result={'passed':False,'real_protocol':True,'disposable_only':True,'normal_player_privileges':True,'errors':[]}
def wait(test,label,seconds=20):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  for peer in peers:peer.pump()
  if test():return
 raise RuntimeError(label+'; '+repr([dict(messages=p.snapshot.get('messages',[]),feedback=p.snapshot.get('classic_ui',{}).get('feedback'),casting=p.snapshot.get('classic_ui',{}).get('casting')) for p in peers]))
def settle(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  for peer in peers:peer.pump()

try:
 with sqlite3.connect(DB) as db:
  assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name
  db.execute("UPDATE Account SET PrivLevel=1, Realm=3 WHERE Name=(SELECT AccountName FROM DOLCharacters WHERE Name='Codexdruid')")
  db.execute("UPDATE DOLCharacters SET Health=200, DeathTime=0, HasGravestone=0, DisabledSpells='',DisabledAbilities='' WHERE Name='Codexdruid'")
  db.execute("UPDATE Mob SET ClassType='DOL.GS.GameTrainingDummy', Name='Codex Pet Training Dummy', Model=2009, Level=1, Realm=0, Flags=0, AggroLevel=0, Speed=0, X=(SELECT Xpos+320 FROM DOLCharacters WHERE Name='Codexdruid'), Y=(SELECT Ypos FROM DOLCharacters WHERE Name='Codexdruid'), Z=(SELECT Zpos FROM DOLCharacters WHERE Name='Codexdruid') WHERE Name IN ('Codex Magic Target','Codex Pet Training Dummy')")
 output=(RUN/'world_pointer_server.log').open('w',encoding='utf-8');handles.append(output)
 server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=output,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 deadline=time.monotonic()+30
 while time.monotonic()<deadline:
  try:
   with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Isolated server unavailable')
 time.sleep(2) # Listening precedes accepting logins in the original core.
 game=Path(str(INSTALL / 'new-client'));sdk=Path(str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64'))
 for character,suffix,root,port in [('Codexdruid','',RUN,19737)]:
  account='codexqa'+hashlib.sha256((RUN.name+suffix).encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name+suffix).encode()).hexdigest()[:24]
  client_env=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'],APPDATA=str(root/'appdata'))
  log=(root/'world_pointer_client.log').open('w',encoding='utf-8');handles.append(log)
  request=root/'Reports/live/logout.request'
  if request.exists():request.unlink()
  client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(game/'godot'),'--script',str(root/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character='+character],cwd=root,env=client_env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  clients.append((client,root));peers.append(Peer(port))

 wait(lambda:peers[0].snapshot.get('classic_ui',{}).get('skills_ready'),'Original player UI ready')
 a=peers[0];ui=lambda:a.snapshot.get('classic_ui',{})
 point=lambda:next(e['position_m'] for e in a.snapshot['entities'] if e['id']=='player:local')
 inventory=a.snapshot['inventory']['items']
 wait(lambda:a.snapshot.get('player_status',{}).get('ready'),'Actual character vitals ready')
 if a.snapshot['player_status']['vitals'].get('sitting'):
  a.send('player_sit',on=False,player_generation=a.snapshot['player_status']['generation'])
  wait(lambda:not a.snapshot['player_status']['vitals'].get('sitting'),'Stand before original spell use')
 def bind(name):
  e=next(e for e in ui()['entries'] if e['name']==name or e['id']==name)
  a.send('ui_assign',bar=2,bank=ui()['banks'][2],slot=9,entry_id=e['id'],entry_token=e['token'])
  wait(lambda:ui()['bars'][2][ui()['banks'][2]][9].get('id')==e['id'],'Bind '+name)
 def use():settle(.2);a.send('ui_use_slot',bar=2,slot=9)
 a.send('target_self');settle(3)
 import sys;sys.path.insert(0,str(ROOT))
 from pet_sight_relay import NativeSightRelay
 relay=NativeSightRelay(a.sock,ROOT,a.session,a.snapshot);a.sock=relay
 wait(lambda:relay.read_report().get('local_animation'),'Native renderer ready',80)
 bind('Call Greater Nature Spirit');use()
 wait(lambda:ui().get('pet',{}).get('valid'),'Original pet summoned',25)
 settle(1)
 pet=lambda:ui().get('pet',{})
 result['pet_initial']=dict(pet());print('pet summoned',pet().get('name'),flush=True)
 # Names and model come from real packets, never substitute a creature.
 wolf=lambda:next((e for e in a.snapshot['entities'] if e.get('id')=='npc:'+str(pet().get('oid'))),{})
 wait(lambda:bool(wolf()),'Original summoned model in entity stream')
 result['pet_model']=wolf()['model_id']
 bind('petcmd:passive');use();wait(lambda:pet()['aggro']==3,'Passive acknowledged')
 bind('petcmd:stay');use();wait(lambda:pet()['walk']==2,'Stay acknowledged');settle(1)
 home=list(wolf()['position_m'])
 start=list(point())
 # Exercise actual walking; each movement is below the bridge's five-metre limit.
 for step in range(5):
  q=list(point());before=list(q);q[2]+=2
  a.send('move',position_m=q,forward_xz=[0,1],speed_mps=2,target_in_view=False)
  wait(lambda:math.dist(point(),before)>1,'Real player walking update')
  settle(.75)
 a.send('move',position_m=list(point()),forward_xz=[0,1],speed_mps=0,target_in_view=False);settle(1)
 result['player_walk_m']=math.dist(start,point());assert result['player_walk_m']>8
 result['stay_distance_m']=math.dist(home,wolf()['position_m']);assert result['stay_distance_m']<.3
 bind('petcmd:follow');use();wait(lambda:pet()['walk']==1,'Follow acknowledged');wait(lambda:math.dist(home,wolf()['position_m'])>.5,'Wolf follows player physically',25)
 result['follow_distance_m']=math.dist(home,wolf()['position_m'])
 enemy=next(e for e in a.snapshot['entities'] if e.get('name')=='Codex Pet Training Dummy');a.send('target',entity_id=enemy['id']);settle(.5)
 bind('petcmd:attack');use();print('pet attack requested',flush=True)
 wait(lambda:wolf().get('combat_active') or wolf().get('combat_visual') or any('attacks' in m.lower() and 'dummy' in m.lower() for m in a.snapshot.get('messages',[])),'Actual pet combat confirmed',25)
 result['attack_confirmed']=True;result['wolf_combat']={k:wolf().get(k) for k in ['state','combat_active','combat_visual','position_m']};settle(3)
 bind('petcmd:passive');use();wait(lambda:pet()['aggro']==3,'Stop combat via original passive order');settle(1)
 bind('petcmd:follow');use();wait(lambda:pet()['walk']==1,'Follow restored')
 bind('petcmd:release');use();wait(lambda:not pet()['valid'],'Release confirmed');settle(1)
 result['released']=True
 a.send('target_self');settle(.3)
 bind('Might of the Redwood');use()
 wait(lambda:ui().get('concentration',{}).get('entries'),'Original maintained self buff cast',20)
 settle(1)
 result['native_los_answers']=relay.answers
 result['native_visuals']=relay.read_report().get('spell_visuals',{})
 result['visual_events']=sum(len(x.get('spell_visuals',[])) for x in a.trace)
 assert result['visual_events']>0,'Real cast packets must publish visible effects'
 result['inventory_unchanged']=a.snapshot['inventory']['items']==inventory;assert result['inventory_unchanged']
 result['passed']=True
except Exception:result['errors'].append(traceback.format_exc())
finally:
 for index,peer in enumerate(peers):
  (RUN/('pet_trace_'+str(index)+'.json')).write_text(json.dumps([dict(seq=x.get('seq'),pet=x.get('classic_ui',{}).get('pet'),spell_visuals=x.get('spell_visuals'),entities=[e for e in x.get('entities',[]) if e.get('model_id') in (102,101,133,1910,2009)]) for x in peer.trace]))
  if peer.session:
   try:peer.send('logout')
   except OSError:pass
 for client,root in clients:
  if client.poll() is None:
   (root/'Reports/live/logout.request').write_text('logout')
   try:client.wait(timeout=100)
   except subprocess.TimeoutExpired:client.kill();client.wait(timeout=10);result['errors'].append('QA client needed forced stop')
 for peer in peers:peer.sock.close()
 if server is not None and server.poll() is None:
  server.stdin.write('exit\n');server.stdin.flush()
  try:server.wait(timeout=40)
  except subprocess.TimeoutExpired:server.kill();server.wait(timeout=10);result['errors'].append('QA server needed forced stop')
 if relay is not None:
  try:result['native_exit']=relay.finish()
  except Exception:result['errors'].append(traceback.format_exc())
 if server is not None and server.poll() is not None:
  with sqlite3.connect(DB) as db:db.execute("UPDATE Account SET PrivLevel=3, Realm=2 WHERE Name=(SELECT AccountName FROM DOLCharacters WHERE Name='Codexdruid')")
 for handle in handles:handle.close()
 result['normal_shutdown']=all(c.returncode==0 for c,_ in clients) and server is not None and server.returncode==0
 result['passed']=result['passed'] and result['normal_shutdown'] and not result['errors']
 (ROOT/'Reports/training_staff_fx_pets/pet_real.json').write_text(json.dumps(result,indent=2))
 print(json.dumps({k:v for k,v in result.items() if k not in ['pet_initial','native_los_answers']},ensure_ascii=True),flush=True)
if not result['passed']:raise SystemExit(1)
