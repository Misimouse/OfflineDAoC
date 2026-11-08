"""Measure original standing and seated regeneration through installed bridge; restore private data and libraries."""
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3,shutil,statistics
import sys
source_qa=Path(os.environ.get("DAOC_BRIDGE_SOURCE_QA",str(ROOT.parent/"DAoC-Enhanced-Godot/source/ue5-bridge/ProtocolQA"))).resolve();assert (source_qa/"central_activation_receipts.py").is_file();sys.path.insert(0,str(source_qa))
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
SOURCE=ROOT/'Godot'
D=ROOT/'RestRegenerationLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
BACKUP=ROOT/'Backups'/('RestRegeneration_'+time.strftime('%Y%m%d-%H%M%S'));BACKUP.mkdir()
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
   if value.get('type')=='snapshot':
    self.snapshot=value
    status=value.get('player_status',{});v=status.get('vitals',{})
    sample={k:v.get(k) for k in ['health','max_health','mana','max_mana','endurance','max_endurance','sitting','alive']}
    if sample.get('health') is not None and (not self.trace or any(self.trace[-1].get(k)!=v for k,v in sample.items())):self.trace.append(dict(at=time.monotonic(),**sample))
 def party(self):return self.snapshot.get('classic_ui',{}).get('party',{})
peers=[];clients=[];handles=[];server=None
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[],'source_inputs':{str(p):digest(p) for p in SOURCE.glob('*.gd')}}
result['source_inputs'][str(INSTALL/'new-client/godot/game/net/server.gd')]=digest(INSTALL/'new-client/godot/game/net/server.gd')

for name in ['gameutils/ClassicRestRegeneration.cs','gameobjects/GamePlayer.cs','propertycalc/HealthRegenerationAmountCalculator.cs','propertycalc/PowerRegenerationAmountCalculator.cs','propertycalc/EnduranceRegenerationAmountCalculator.cs']:
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
   db.execute('UPDATE DOLCharacters SET Class=47,Level=20,Health=1,Mana=1,Endurance=1,Region=200,Xpos=341975,Ypos=?,Zpos=5216,HCFlag=0 WHERE DOLCharacters_ID=?',(469306+(100 if c['Name']=="Codexfriend" else 0),c['DOLCharacters_ID']))
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
 def state(peer):return peer.snapshot.get('player_status',{})
 def vitals(peer):return state(peer).get('vitals',{})
 wait(lambda:all(state(p).get('ready') for p in peers),'Original status arrives')
 result['checks']['low_positive_health_is_alive']=all(vitals(p).get('alive') and 0<vitals(p)['health']<vitals(p)['max_health'] for p in peers)
 a.send('player_sit',on=False,player_generation=state(a)['generation'])
 b.send('player_sit',on=True,player_generation=state(b)['generation'])
 wait(lambda:not vitals(a).get('sitting') and vitals(b).get('sitting') and not state(b).get('posture_pending'),'Original server confirms resting posture')
 result['checks']['posture_acknowledged_by_server']=True
 began=time.monotonic();a.trace=[];b.trace=[];settle(27)
 samples=[list(p.trace) for p in peers]
 def transitions(series,key):
  return [row for i,row in enumerate(series) if i and row[key]>series[i-1][key]]
 def intervals(series,key):
  rows=transitions(series,key);return [q['at']-p['at'] for p,q in zip(rows,rows[1:])]
 metrics={}
 for label,series,period in [('standing',samples[0],6),('sitting',samples[1],3)]:
  health=intervals(series,'health');mana=intervals(series,'mana');endu=transitions(series,'endurance')
  result['checks'][label+'_health_original_interval']=len(health)>=2 and all(abs(v-period)<.8 for v in health)
  result['checks'][label+'_power_original_interval']=len(mana)>=2 and all(abs(v-period)<.8 for v in mana)
  result['checks'][label+'_health_only_increases_without_combat']=bool(series) and all(y['health']>=x['health'] for x,y in zip(series,series[1:]))
  result['checks'][label+'_endurance_recovers']=bool(endu)
  metrics[label]={'health_intervals':health,'power_intervals':mana,'samples':series}
 result['checks']['seated_health_ticks_faster']=statistics.median(intervals(samples[1],'health'))<statistics.median(intervals(samples[0],'health'))
 result['checks']['seated_power_ticks_faster']=statistics.median(intervals(samples[1],'mana'))<statistics.median(intervals(samples[0],'mana'))
 before=dict(vitals(b));b.send('player_sit',on=False,player_generation=state(b)['generation']);wait(lambda:not vitals(b).get('sitting') and not state(b).get('posture_pending'),'Standing again confirmed')
 result['checks']['standing_keeps_positive_vitals']=vitals(b)['health']>=before['health'] and vitals(b)['mana']>=before['mana']
 (D/'measurements.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
 (D/'active_snapshot.json').write_text(json.dumps(b.snapshot),encoding='utf-8')
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
