"""Exercise original concentration lifecycle with ordinary disposable accounts; restore private data and libraries."""
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3,shutil
import sys
source_qa=Path(os.environ.get("DAOC_BRIDGE_SOURCE_QA",str(ROOT.parent/"DAoC-Enhanced-Godot/source/ue5-bridge/ProtocolQA"))).resolve();assert (source_qa/"central_activation_receipts.py").is_file();sys.path.insert(0,str(source_qa))
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
SOURCE=ROOT/'Godot'
D=ROOT/'ConcentrationLifecycleLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
BACKUP=ROOT/'Backups'/('ConcentrationLifecycle_'+time.strftime('%Y%m%d-%H%M%S'));BACKUP.mkdir()
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
 def conc(peer=a):return peer.snapshot.get('classic_ui',{}).get('concentration',{})
 def entries():return conc().get('entries',[])
 def cancel(row):a.send('conc_cancel',concentration_index=row['index'],concentration_token=row['token'])
 wait(lambda:conc().get('pool_known') and conc().get('visible'),'Original caster concentration pool')
 result['checks']['original_caster_pool_visible']=conc()['maximum']>0
 # Existing private effects may have been restored from the private QA baseline.
 for i in range(20):
  if not entries():break
  before=len(entries());cancel(entries()[0]);wait(lambda:len(entries())<before,'Original existing concentration cancellation')
 assert not entries();wait(lambda:conc()['remaining']==conc()['maximum'],'Original empty concentration pool restored')
 result['checks']['existing_private_effects_cancel_with_server_confirmation']=True
 wait(lambda:any(e.get('name')=='Codexfriend' for e in a.snapshot.get('entities',[])),'Friendly ordinary recipient exists')
 target=next(e for e in a.snapshot['entities'] if e.get('name')=='Codexfriend')
 def cast(name,own):
  if own:
   a.send('target_self');wait(lambda:a.snapshot.get('interaction',{}).get('target',{}).get('id')=='player:local','Self target')
  else:
   a.send('target',entity_id=target['id']);wait(lambda:a.snapshot.get('interaction',{}).get('target',{}).get('id')==target['id'],'Friend target')
  e=next(e for e in a.snapshot['classic_ui']['entries'] if e.get('kind')=='spell' and e.get('name')==name)
  a.send('ui_use',entry_id=e['id'],entry_token=e['token'])
 cast('Strength of the Tree',True);wait(lambda:len(entries())==1 and entries()[0]['owner']=='Codexdruid','Original self concentration buff',20)
 own=dict(entries()[0]);result['checks']['self_cast_creates_original_owner_entry']=own['conc']==4 and own['icon']>=0
 wait(lambda:conc()['maximum']-conc()['remaining']==own['conc'],'Original self concentration cost')
 result['checks']['original_self_cost_deducted']=True
 before_effects=len(a.snapshot['classic_ui'].get('effects',[]));cast('Dexterity of the Wolf',True)
 wait(lambda:len(entries())==2,'Second original self concentration buff',20)
 other=next(dict(e) for e in entries() if e['name']!=own['name']);wait(lambda:conc()['maximum']-conc()['remaining']==own['conc']+other['conc'],'Original shared concentration cost')
 result['checks']['second_distinct_buff_keeps_original_icon_and_cost']=other['conc']>0 and other['icon']>=0 and other['owner']=='Codexdruid'
 result['checks']['original_pool_matches_both_costs']=True
 wait(lambda:len(a.snapshot['classic_ui'].get('effects',[]))>before_effects,'Original second effect visible')
 result['checks']['second_original_effect_visible']=True
 b.send('conc_cancel',concentration_index=other['index'],concentration_token=other['token']);settle(.5)
 result['checks']['another_account_cannot_cancel_caster_effect']=len(entries())==2 and 'effect has changed' in conc(b).get('feedback','').lower()
 (D/'active_snapshot.json').write_text(json.dumps(a.snapshot),encoding='utf-8')
 # The second server list supersedes the token captured before it existed.
 cancel(own);settle(.5);result['checks']['stale_list_token_cannot_cancel_current_buff']=len(entries())==2 and 'effect has changed' in conc().get('feedback','').lower()
 cancel(other);wait(lambda:len(entries())==1 and entries()[0]['name']==own['name'],'Cancel exact selected original effect')
 wait(lambda:conc()['maximum']-conc()['remaining']==own['conc'],'Only selected cost refunded')
 result['checks']['selected_cancellation_preserves_other_buff']=True
 wait(lambda:len(a.snapshot['classic_ui'].get('effects',[]))==before_effects,'Selected self effect removed by server')
 result['checks']['selected_self_effect_removal_confirmed']=True
 current=dict(entries()[0]);cancel(current);wait(lambda:not entries() and conc()['remaining']==conc()['maximum'],'Final original effect removed and pool restored')
 result['checks']['last_cancellation_restores_actual_pool']=True
 cancel(current);settle(.5);result['checks']['removed_effect_token_cannot_be_reused']=not entries() and 'effect has changed' in conc().get('feedback','').lower()
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
