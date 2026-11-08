"""Exercise candidate Stealth UI and quickbar against the original server specialization handler."""
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3,shutil
import sys
source_qa=Path(os.environ.get("DAOC_BRIDGE_SOURCE_QA",str(ROOT.parent/"DAoC-Enhanced-Godot/source/ue5-bridge/ProtocolQA"))).resolve();assert (source_qa/"central_activation_receipts.py").is_file();sys.path.insert(0,str(source_qa))
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
SOURCE=source_qa.parent/'Godot'
D=ROOT/'StealthLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
BACKUP=ROOT/'Backups'/('StealthAfter_'+time.strftime('%Y%m%d-%H%M%S'));BACKUP.mkdir()
config_backups=[];candidate_files=[];layout_backups=[];backed=False
normal=verify_files(ROOT)
normal_paths=[ROOT/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll',INSTALL/'runtime/server/GameServer.dll',INSTALL/'runtime/server/lib/GameServer.dll']
normal_hashes={str(p):digest(p) for p in normal_paths}
def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row;assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name;return db
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
peers=[];clients=[];handles=[];server=None
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[],'source_inputs':{str(p):digest(p) for p in SOURCE.glob('*.gd')}}
result['source_inputs'][str(INSTALL/'new-client/godot/game/net/server.gd')]=digest(INSTALL/'new-client/godot/game/net/server.gd')

for name in ['skillhandler/StealthSpecHandler.cs','ECS-Effects/StealthECSEffect.cs','packets/Client/168/UseSkillHandler.cs','packets/Server/PacketLib168.cs']:
 p=source_qa.parents[1]/'server/GameServer'/name;result['source_inputs'][str(p)]=digest(p)

def wait(test,label,seconds=20):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  for peer in peers:peer.pump()
  if test():return
 raise RuntimeError(label+'; '+repr([p.snapshot.get('messages',[]) for p in peers]))
def settle(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  for peer in peers:peer.pump()
try:
 for port in [10351,19737,19738]:
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):raise RuntimeError('Private QA port occupied')
  except (ConnectionRefusedError,socket.timeout):pass
 with checked() as db:
  dest=sqlite3.connect(BACKUP/'before.sqlite3.db');db.backup(dest);dest.close();backed=True
  rows=db.execute("SELECT * FROM DOLCharacters WHERE Name IN ('Codexdruid','Codexfriend')").fetchall();assert len(rows)==2
  leader=dict(next(c for c in rows if c['Name']=='Codexdruid'))
  for c in rows:
   db.execute('UPDATE Account SET PrivLevel=1,Realm=3 WHERE Name=?',(c['AccountName'],))
   db.execute('UPDATE DOLCharacters SET Class=?,Level=20,Health=5000,Mana=100,Endurance=100,Region=200,Xpos=341975,Ypos=?,Zpos=5216,HCFlag=0 WHERE DOLCharacters_ID=?',(47 if c['Name']=="Codexfriend" else 49,469306+(2000 if c['Name']=="Codexfriend" else 0),c['DOLCharacters_ID']))
  result['checks']['ordinary_accounts_only']=all(db.execute('SELECT PrivLevel FROM Account WHERE Name=?',(c['AccountName'],)).fetchone()[0]==1 for c in rows)
 for n,root in enumerate([RUN,RUN/'friend-session']):
  assert root.resolve().is_relative_to(RUN)
  config=root/'bridge_config.json';config_backups.append((config,config.read_bytes()))
  cfg=json.loads(config.read_text());cfg['initial_spawn_m']=[(leader['Xpos']-35*8192)*.025,leader['Zpos']*.025,(leader['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
  for q in SOURCE.glob('*.gd'):shutil.copy2(q,root/'Godot'/q.name)
  layout=root/'Client/Saved/ClassicUI'/(hashlib.sha256(("codexfriend" if n else "codexdruid").encode()).hexdigest()+'.json')
  assert layout.resolve().is_relative_to(RUN);layout_backups.append((layout,layout.read_bytes() if layout.exists() else None))
  q=root/'Godot/visual_bridge.gd';q.write_text(q.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = '+str(19737+n)),encoding='utf-8')
 candidate_root=ROOT/'GuildWindowLab/ServerCandidate';candidate=json.loads((candidate_root/'build_receipt.json').read_text());assert candidate['passed']
 for folder in [SERVER,SERVER/'lib',SERVER/'win-x64']:
  for name,expected in candidate['binaries_sha256'].items():
   target=folder/name
   if not target.exists():continue
   assert target.resolve().is_relative_to(RUN);origin=Path(candidate['libraries'])/name;assert digest(origin)==expected
   saved=BACKUP/('server_'+str(len(candidate_files))+'_'+name);shutil.copy2(target,saved);candidate_files.append((target,saved));shutil.copy2(origin,target)
 output=(D/'server.log').open('w',encoding='utf-8');handles.append(output)
 server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=output,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 deadline=time.monotonic()+40
 while time.monotonic()<deadline:
  try:
   with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Isolated server unavailable')
 game=INSTALL/'new-client';sdk=ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64'
 for character,suffix,root,port in [('Codexdruid','',RUN,19737),('Codexfriend',':friend',RUN/'friend-session',19738)]:
  account='codexqa'+hashlib.sha256((RUN.name+suffix).encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name+suffix).encode()).hexdigest()[:24]
  ce=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'],APPDATA=str(root/'appdata'))
  log=(D/(character+'_client.log')).open('w',encoding='utf-8');handles.append(log);(root/'Reports/live/logout.request').unlink(missing_ok=True)
  client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(root/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character='+character],cwd=root,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  clients.append((client,root));peers.append(Peer(port))
 wait(lambda:all(p.snapshot.get('classic_ui',{}).get('skills_ready') for p in peers),'Both ordinary players ready',40)
 a,b=peers
 def ui(peer=a):return peer.snapshot.get('classic_ui',{})
 def hidden(peer=a):return any(int(e.get('effect_icon',-1))==0x193 for e in ui(peer).get('effects',[]))
 def sprinting():return any('sprint' in e.get('name','').lower() for e in ui().get('effects',[]))
 def stealth_entry():return next(e for e in ui()['entries'] if e.get('name')=='Stealth' and e.get('id','').startswith('srv:spec:'))
 def use_stealth():
  e=stealth_entry();a.send('ui_use',entry_id=e['id'],entry_token=e['token'])
 wait(lambda:any(e.get('name')=='Stealth' for e in ui().get('entries',[])),'Original Stealth action reaches native UI catalogue')
 base=a.snapshot['max_speed_mps'];result['checks']['original_stealth_action_is_available']=stealth_entry()['kind']=='ability'
 result['checks']['ordinary_druid_does_not_receive_stealth']=not any(e.get('name')=='Stealth' for e in ui(b).get('entries',[]))
 e=stealth_entry();a.send('ui_use',entry_id=e['id'],entry_token='stale');settle(.3)
 result['checks']['stale_ui_action_refused']=not hidden()
 use_stealth();wait(lambda:hidden() and a.snapshot['max_speed_mps']<base,'Original Stealth effect and speed confirmed')
 result['checks']['original_server_hides_after_ui_action']=True
 def own_render():return next((r for r in a.snapshot.get('entities',[]) if r.get('id')=='player:local'),{})
 wait(lambda:own_render().get('stealth_render_known') and own_render().get('stealth_render_hidden'),'Original local model-type packet reaches native snapshot')
 result['checks']['local_hidden_presentation_is_server_confirmed']=True
 use_stealth();settle(.3)
 result['checks']['original_two_second_toggle_limit_preserved']=hidden() and any('wait' in m.lower() and 'hide' in m.lower() for m in a.snapshot.get('messages',[]))
 settle(2.1);use_stealth();wait(lambda:not hidden() and abs(a.snapshot['max_speed_mps']-base)<.01,'Original Stealth toggles off after allowed delay')
 result['checks']['original_server_reveals_and_restores_speed']=True
 wait(lambda:own_render().get('stealth_render_known') and not own_render().get('stealth_render_hidden'),'Original local type-two restores visible presentation')
 result['checks']['local_visible_presentation_is_server_confirmed']=True
 wait(lambda:any(e.get('name')=='Codexdruid' for e in b.snapshot.get('entities',[])),'Original reveal creates Nightshade for normal observer')
 observer_id=next(e['id'] for e in b.snapshot['entities'] if e.get('name')=='Codexdruid')
 b.send('target',entity_id=observer_id);wait(lambda:b.snapshot.get('interaction',{}).get('target',{}).get('id')==observer_id,'Observer targets authoritatively revealed Nightshade')
 result['checks']['observer_sees_original_reappearance']=True
 a.send('ui_bank',bar=2,bank=0);wait(lambda:ui()['banks'][2]==0,'Private quickbar bank')
 e=stealth_entry();a.send('ui_assign',bar=2,bank=0,slot=9,entry_id=e['id'],entry_token=e['token']);wait(lambda:ui()['bars'][2][0][9].get('id')==e['id'],'Original Stealth dragged to private quickbar')
 result['checks']['existing_quickbar_accepts_stealth']=True
 settle(2.1);a.send('ui_use_slot',bar=2,slot=9);wait(lambda:hidden(),'Original Stealth activates from bar')
 result['checks']['quickbar_uses_original_spec_handler']=True
 wait(lambda:not any(e.get('id')==observer_id for e in b.snapshot.get('entities',[])),'Original ObjectDelete removes hidden player from observer')
 settle(.6)
 result['checks']['observer_cannot_keep_hidden_player_rendered']=not any(e.get('id')==observer_id for e in b.snapshot.get('entities',[]))
 result['checks']['hidden_target_is_cleared']=b.snapshot.get('interaction',{}).get('target',{}).get('id')!=observer_id
 sp=next(e for e in ui()['entries'] if e.get('name')=='Sprint');a.send('ui_use',entry_id=sp['id'],entry_token=sp['token']);settle(.5)
 result['checks']['server_refuses_sprint_while_hidden']=hidden() and not sprinting()
 settle(2.1);a.send('ui_use_slot',bar=2,slot=9);wait(lambda:not hidden(),'Quickbar reveals through original handler')
 wait(lambda:any(e.get('id')==observer_id for e in b.snapshot.get('entities',[])),'Original second reveal restores observer entity')
 result['checks']['quickbar_reveals_normally']=True
 (D/'active_snapshot.json').write_text(json.dumps(a.snapshot),encoding='utf-8')
 result['passed']=all(result['checks'].values())
except Exception:result['errors'].append(traceback.format_exc())
finally:
 for i,peer in enumerate(peers):
  (D/('snapshot_'+str(i)+'.json')).write_text(json.dumps(peer.snapshot),encoding='utf-8')
  if peer.session:
   try:peer.send('logout')
   except OSError:pass
 for client,root in clients:
  if client.poll() is None:
   (root/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
   try:client.wait(timeout=100)
   except subprocess.TimeoutExpired:client.kill();client.wait();result['errors'].append('Private client forced stop')
 for peer in peers:peer.sock.close()
 if server and server.poll() is None:
  server.stdin.write('exit\n');server.stdin.flush()
  try:server.wait(timeout=45)
  except subprocess.TimeoutExpired:server.kill();server.wait();result['errors'].append('Private server forced stop')
 for handle in handles:handle.close()
 for target,saved in reversed(candidate_files):assert target.resolve().is_relative_to(RUN);shutil.copy2(saved,target)
 for config,raw in config_backups:config.write_bytes(raw)
 for path,raw in layout_backups:
  assert path.resolve().is_relative_to(RUN)
  if raw is None:path.unlink(missing_ok=True)
  else:path.write_bytes(raw)
 if backed:
  with checked() as db:
   src=sqlite3.connect(BACKUP/'before.sqlite3.db');src.backup(db);src.close()
  result['database_restored']=True
 result['private_server_restored']=bool(candidate_files)
 result['normal_shutdown']=bool(clients) and all(c.returncode==0 for c,_ in clients) and server is not None and server.returncode==0
 result['normal_runtime_unchanged']=all(digest(Path(p))==h for p,h in normal_hashes.items())
 result['passed']=result['passed'] and result['normal_shutdown'] and result.get('database_restored',False) and result['normal_runtime_unchanged'] and not result['errors'] and all(digest(Path(p))==h for p,h in result['source_inputs'].items())
 (D/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='source_inputs'}));assert result['passed']
