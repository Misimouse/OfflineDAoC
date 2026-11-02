import sys as _bridge_sys
from pathlib import Path as _BridgePath
_bridge_sys.path.insert(0,str(_BridgePath(__file__).resolve().parents[1]))
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3
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
  assert db.execute("SELECT Class,Level FROM DOLCharacters WHERE Name='Codexdruid'").fetchone()==(47,50)
  db.execute("UPDATE DOLCharacters SET Health=200, DeathTime=0, HasGravestone=0, DisabledSpells='',DisabledAbilities='' WHERE Name='Codexdruid'")
  db.execute("UPDATE Mob SET Flags=Flags & ~16, AggroLevel=0, Speed=0, X=(SELECT Xpos FROM DOLCharacters WHERE Name='Codexdruid'), Y=(SELECT Ypos+400 FROM DOLCharacters WHERE Name='Codexdruid'), Z=(SELECT Zpos FROM DOLCharacters WHERE Name='Codexdruid') WHERE Name='Codex Magic Target'")
  db.execute("UPDATE Account SET PrivLevel=1, Realm=3 WHERE Name=(SELECT AccountName FROM DOLCharacters WHERE Name='Codexdruid')")
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
 wait(lambda:all(p.snapshot.get('classic_ui',{}).get('skills_ready') for p in peers),'Both actual players ready')
 a=peers[0]
 def target():return a.snapshot.get('interaction',{}).get('target',{}).get('id')
 def spawn(kind):
  previous=max([e['id'] for e in a.snapshot.get('chat',{}).get('entries',[])],default=0)
  a.send('chat',text='/mob create '+kind+' 3')
  def created():return [e for e in a.snapshot.get('chat',{}).get('entries',[]) if e['id']>previous and e['text'].startswith('Mob created: OID=')]
  wait(lambda:bool(created()),'Original creation response identifies exact new object')
  oid=int(created()[-1]['text'].split('OID=')[1]);entity='npc:'+str(oid)
  wait(lambda:any(e['id']==entity for e in a.snapshot.get('entities',[])),'Exact created NPC is available')
  return next(e for e in a.snapshot['entities'] if e['id']==entity)

 ui=lambda:a.snapshot.get('classic_ui',{})
 vitals=lambda:a.snapshot.get('player_status',{}).get('vitals',{})
 cast=lambda:ui().get('casting',{})
 def point():return next(e['position_m'] for e in a.snapshot['entities'] if e['id']=='player:local')
 def bind(name,slot=9):
  e=next(e for e in ui()['entries'] if e['name']==name)
  a.send('ui_assign',bar=2,bank=ui()['banks'][2],slot=slot,entry_id=e['id'],entry_token=e['token'])
  wait(lambda:ui()['bars'][2][ui()['banks'][2]][slot].get('id')==e['id'],'Original shortcut acknowledgement')
  return e
 def use(slot=9):a.send('ui_use_slot',bar=2,slot=slot)
 def stationary():a.send('move',position_m=point(),forward_xz=[0,1],speed_mps=0,target_in_view=True,target_entity_id='player:local')
 inventory=a.snapshot['inventory']['items'];a.send('target_self');stationary();settle(3)
 for row in list(ui().get('concentration',{}).get('entries',[])):
  a.send('conc_cancel',concentration_index=row['index'],concentration_token=row['token']);wait(lambda:not ui()['concentration'].get('pending'),'Clean previous disposable maintained effect');settle(.3)

 # A normal spell is interrupted by movement before its server result.
 bind('Minor Apotheosis');seq=cast().get('seq',0);use()
 wait(lambda:cast().get('seq',0)>seq and cast().get('phase')=='casting','Normal cast starts before movement')
 q=point();q[0]+=.1;a.send('move',position_m=q,forward_xz=[1,0],speed_mps=1,target_in_view=True,target_entity_id='player:local')
 wait(lambda:cast().get('phase')=='interrupted','Actual movement interrupts preparation')
 stationary();settle(1);result['movement_interrupted']=True
 # Start injured only in the disposable DB; confirm the actual heal packet raises life.
 before=vitals()['health'];bind('Minor Apotheosis');seq=cast().get('seq',0);use()
 wait(lambda:cast().get('seq',0)>seq and cast().get('phase')=='casting','Server-confirmed heal begins')
 mana=vitals()['mana'];wait(lambda:cast().get('phase')=='released','Heal released');wait(lambda:vitals()['health']>before,'Actual heal increases health')
 result['heal']={'before':before,'after':vitals()['health'],'power_before':mana,'power_after':vitals()['mana']};assert vitals()['mana']<mana
 # Level12 instant was obtained through the real trainer in the preceding QA run.
 wait(lambda:any(e['name']=="Nature's Appreciation" for e in ui()['entries']),'Original instant heal learned')
 e=bind("Nature's Appreciation");settle(.4);seq=cast().get('seq',0);use()
 wait(lambda:ui().get('reuse_ms',{}).get(e['id'],0)>0,'Original instant cooldown')
 result['instant_heal']={'id':e['id'],'reuse_ms':ui()['reuse_ms'][e['id']],'cast':cast()};assert not(cast().get('seq',0)>seq and cast().get('phase')=='casting')
 use();wait(lambda:ui().get('feedback')=='This action is still recovering.','Duplicate instant use blocked by actual server reuse timer')
 result['reuse_blocks_repeat']=True;first=ui()['reuse_ms'][e['id']];settle(1.2);assert 0<ui()['reuse_ms'][e['id']]<first;result['reuse_counts_down']=True
 # Sustained buff consumes original concentration and cancels through the original protocol.
 bind('Might of the Redwood');a.send('target_self');stationary();seq=cast().get('seq',0);use()
 wait(lambda:cast().get('seq',0)>seq and cast().get('phase')=='casting','Buff preparation')
 wait(lambda:bool(ui().get('concentration',{}).get('entries')),'Concentration buff applied')
 row=next(x for x in ui()['concentration']['entries'] if x['name'].startswith('Might of the'));result['buff_applied']=row
 a.send('conc_cancel',concentration_index=row['index'],concentration_token=row['token'])
 wait(lambda:not any(x['name'].startswith('Might of the') for x in ui()['concentration']['entries']),'Buff cancelled by server')
 wait(lambda:not any(x['name'].startswith('Might of the') for x in ui()['effects']),'Buff icon removed')
 result['buff_and_icon_removed']=True
 # Physical UE geometry answers actual server LOS, no blanket true reply.
 import sys;sys.path.insert(0,str(ROOT))
 from magic_sight_relay import NativeSightRelay
 relay=NativeSightRelay(a.sock,ROOT,a.session,a.snapshot);a.sock=relay
 wait(lambda:relay.read_report().get('local_animation'),'UE ready',80)
 enemy=next(e for e in a.snapshot['entities'] if e.get('name')=='Codex Magic Target');a.send('target',entity_id=enemy['id']);settle(.2)
 # Move 3m from the created creature, face it and use native visibility.
 q=point();q[0]+=1
 a.send('move',position_m=q,forward_xz=[1,0],speed_mps=2,target_in_view=True,target_entity_id=enemy['id']);settle(.5)
 a.send('target',entity_id=enemy['id'])
 q=point();enemy=next(e for e in a.snapshot['entities'] if e['id']==enemy['id']);dx=enemy['position_m'][0]-q[0];dz=enemy['position_m'][2]-q[2];length=max(.001,(dx*dx+dz*dz)**.5);facing=[dx/length,dz/length]
 a.send('move',position_m=q,forward_xz=facing,speed_mps=0,target_in_view=True,target_entity_id=enemy['id']);settle(.3)
 relay.start_probe(enemy['id']);wait(lambda:relay.probe_result is not None,'Native clear geometry probe');assert relay.probe_result
 bind('Degeneration');seq=cast().get('seq',0);use()
 wait(lambda:cast().get('seq',0)>seq and cast().get('phase')=='casting','Damage-over-time preparation')
 wait(lambda:cast().get('phase')=='released','Damage-over-time release')
 wait(lambda:any('Degeneration' in m and ('damage' in m.lower() or 'hit' in m.lower()) for m in a.snapshot.get('messages',[])) or any(x['id']==enemy['id'] and x.get('health',1)<1 for x in a.snapshot['entities']),'Actual hostile spell damage')
 result['hostile_damage']=True;settle(1)
 # Harmful instant is a legitimate movement exception and must not acquire a windup bar.
 e=bind('Bursting Undergrowth');seq=cast().get('seq',0);q=point();q[2]+=.05
 a.send('move',position_m=q,forward_xz=facing,speed_mps=.5,target_in_view=True,target_entity_id=enemy['id']);use()
 wait(lambda:ui().get('reuse_ms',{}).get(e['id'],0)>0,'Harmful instant accepted while moving')
 a.send('move',position_m=point(),forward_xz=facing,speed_mps=0,target_in_view=True,target_entity_id=enemy['id'])
 result['moving_instant']={'reuse_ms':ui()['reuse_ms'][e['id']],'casting':cast()};assert not(cast().get('seq',0)>seq and cast().get('phase')=='casting')
 result['native_los_answers']=relay.answers;assert relay.answers and all(x['visible'] for x in relay.answers)
 settle(26) # Let the original DoT finish before a normal saved logout.
 result['alive_after_hostile_test']=vitals().get('health',0)>0;assert result['alive_after_hostile_test']
 result['inventory_unchanged']=a.snapshot['inventory']['items']==inventory;assert result['inventory_unchanged']
 (ROOT/'Reports/magic_roundtrip/real_snapshot.json').write_text(json.dumps(a.snapshot),encoding='utf-8')
 result['passed']=True

except Exception:result['errors'].append(traceback.format_exc())
finally:
 for index,peer in enumerate(peers):
  (RUN/('world_pointer_trace_'+str(index)+'.json')).write_text(json.dumps(peer.trace))
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
 (ROOT/'Reports/magic_roundtrip/real_result.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result,ensure_ascii=False),flush=True)
if not result['passed']:raise SystemExit(1)
