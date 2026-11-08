"""Exercise original timed spell-effect lifecycle with ordinary disposable accounts; restore private data and libraries."""
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3,shutil
import sys
source_qa=Path(os.environ.get("DAOC_BRIDGE_SOURCE_QA",str(ROOT.parent/"DAoC-Enhanced-Godot/source/ue5-bridge/ProtocolQA"))).resolve();assert (source_qa/"central_activation_receipts.py").is_file();sys.path.insert(0,str(source_qa))
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
SOURCE=ROOT/'Godot'
D=ROOT/'TimedEffectsLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
BACKUP=ROOT/'Backups'/('TimedEffects_'+time.strftime('%Y%m%d-%H%M%S'));BACKUP.mkdir()
config_backups=[];candidate_files=[];backed=False
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
  leader=next(c for c in rows if c['Name']=='Codexdruid')
  for c in rows:
   db.execute('UPDATE Account SET PrivLevel=1,Realm=3 WHERE Name=?',(c['AccountName'],))
   db.execute('UPDATE DOLCharacters SET Region=?,Xpos=?,Ypos=?,Zpos=?,HCFlag=0 WHERE DOLCharacters_ID=?',(leader['Region'],leader['Xpos']+(100 if c['Name']=='Codexfriend' else 0),leader['Ypos'],leader['Zpos'],c['DOLCharacters_ID']))
  db.execute("UPDATE DOLCharacters SET Class=48,Level=50,Mana=300,SerializedSpecs='Nurture|1;Regrowth|1;Music|49',SerializedAbilities='',SerializedRealmAbilities='' WHERE Name='Codexdruid'")
  result['checks']['ordinary_accounts_only']=all(db.execute('SELECT PrivLevel FROM Account WHERE Name=?',(c['AccountName'],)).fetchone()[0]==1 for c in rows)
 for n,root in enumerate([RUN,RUN/'friend-session']):
  assert root.resolve().is_relative_to(RUN)
  config=root/'bridge_config.json';config_backups.append((config,config.read_bytes()))
  cfg=json.loads(config.read_text());cfg['initial_spawn_m']=[(leader['Xpos']-35*8192)*.025,leader['Zpos']*.025,(leader['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
  for q in SOURCE.glob('*.gd'):shutil.copy2(q,root/'Godot'/q.name)
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
 def effects():return a.snapshot.get('classic_ui',{}).get('effects',[])
 name='Hymn of Body Guarding'
 def matching():return [e for e in effects() if e.get('name')==name]
 def remaining(row):return a.snapshot['classic_ui']['effects_remaining_ms'].get(row['id'],-1)
 wait(lambda:any(e.get('name')==name and e.get('kind')=='spell' for e in a.snapshot['classic_ui']['entries']),'Original ordinary Bard resistance chant')
 result['checks']['original_class_spell_received']=a.snapshot['classic_ui']['info'].get('class_name')=='Bard'
 a.send('target_self');wait(lambda:a.snapshot.get('interaction',{}).get('target',{}).get('id')=='player:local','Self target')
 entry=next(e for e in a.snapshot['classic_ui']['entries'] if e.get('name')==name and e.get('kind')=='spell')
 def activate():
  current=next(e for e in a.snapshot['classic_ui']['entries'] if e.get('name')==name and e.get('kind')=='spell')
  wait(lambda:a.snapshot['classic_ui'].get('reuse_ms',{}).get(current['id'],0)<=0,'Original spell recovery completes before next activation',35)
  a.send('ui_use',entry_id=current['id'],entry_token=current['token'])
 activate();wait(lambda:len(matching())==1,'Original short pulsing effect appears',20)
 first=dict(matching()[0]);result['checks']['original_effect_icon_and_duration']=first['icon']>=0 and first['until_ms']>0 and remaining(first)>0
 result['checks']['beneficial_effect_not_negative']=not first['negative']
 a.send('ui_detail',entry_id=first['id'],entry_token=first['token']);wait(lambda:a.snapshot['classic_ui'].get('detail',{}).get('status') in ['ready','unavailable'] or not a.snapshot['classic_ui'].get('detail'),'Original effect description response')
 result['checks']['effect_description_does_not_consume_spell']=len(matching())==1
 # Observe actual original five-second effects being refreshed by the active chant.
 before=first['until_ms'];settle(8.5)
 wait(lambda:len(matching())==1 and matching()[0]['until_ms']>before,'Original pulse refreshes duration without duplicate icons')
 renewed=dict(matching()[0]);result['checks']['pulse_refreshes_one_existing_effect']=renewed['until_ms']>before and len(matching())==1
 result['checks']['renewal_replaces_expired_identity']=renewed['token']!=first['token']
 a.send('ui_detail',entry_id=first['id'],entry_token=first['token']);settle(.25)
 result['checks']['stale_effect_identity_rejected']='entry has changed' in a.snapshot['classic_ui'].get('feedback','').lower()
 (D/'active_snapshot.json').write_text(json.dumps(a.snapshot),encoding='utf-8')
 activate();wait(lambda:not matching(),'Stopping original chant removes its effect after the original duration',18)
 result['checks']['original_server_removes_stopped_effect']=True
 result['checks']['removed_timer_entry_disappears']=renewed['id'] not in a.snapshot['classic_ui'].get('effects_remaining_ms',{})
 a.send('ui_detail',entry_id=renewed['id'],entry_token=renewed['token']);settle(.25)
 result['checks']['removed_effect_cannot_be_inspected']='entry has changed' in a.snapshot['classic_ui'].get('feedback','').lower()
 # A second activation must create a fresh confirmed identity, not restore stale local state.
 settle(.3);activate();wait(lambda:len(matching())==1,'Original second chant activation',20)
 second=dict(matching()[0]);result['checks']['second_activation_has_fresh_identity']=second['token']!=renewed['token']
 settle(8.5);activate();wait(lambda:not matching(),'Original second chant stop',18)
 result['checks']['repeat_stop_leaves_no_effect_or_timer']=second['id'] not in a.snapshot['classic_ui'].get('effects_remaining_ms',{})
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
 if backed:
  with checked() as db:
   src=sqlite3.connect(BACKUP/'before.sqlite3.db');src.backup(db);src.close()
  result['database_restored']=True
 result['private_server_restored']=bool(candidate_files)
 result['normal_shutdown']=bool(clients) and all(c.returncode==0 for c,_ in clients) and server is not None and server.returncode==0
 result['normal_runtime_unchanged']=all(digest(Path(p))==h for p,h in normal_hashes.items())
 result['passed']=result['passed'] and result['normal_shutdown'] and result.get('database_restored',False) and result['normal_runtime_unchanged'] and not result['errors'] and all(digest(Path(p))==h for p,h in result['source_inputs'].items())
 (D/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='source_inputs'}));assert result['passed']
