"""Audit missing original Stealth activation against a private original protocol request."""
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3,shutil
import sys
source_qa=Path(os.environ.get("DAOC_BRIDGE_SOURCE_QA",str(ROOT.parent/"DAoC-Enhanced-Godot/source/ue5-bridge/ProtocolQA"))).resolve();assert (source_qa/"central_activation_receipts.py").is_file();sys.path.insert(0,str(source_qa))
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
STEALTH_PROBE='extends Node\nvar gateway:Node\nvar phase:=0\nvar began:=0\nvar index:=-1\nvar report:Dictionary={}\nfunc hidden()->bool:\n    for e in gateway.server.effects.values():\n        if int(e.get("icon",-1))==0x193:return true\n    return false\nfunc request()->void:\n    var p=gateway.server.to_region(207,gateway.position)\n    gateway.server.client.call("UseSkill",p.x,p.y,p.z,0.0,gateway.heading,false,index,0)\nfunc _process(_delta:float)->void:\n    if phase==99 or gateway.server==null or not gateway.server.playing:return\n    if phase==0:\n        if not gateway.classic_ui.skills_received:return\n        for i in gateway.server.skills.size():\n            var s:Dictionary=gateway.server.skills[i]\n            if int(s.get("page",-1))==0 and String(s.get("name",""))=="Stealth" and int(s.get("level",0))>0:index=i\n        if index<0:return\n        var available:=false\n        for e in gateway.classic_ui.entries.values():\n            if String(e.get("name",""))=="Stealth":available=true\n        report={"server_spec_index":index,"server_spec_available":true,"bridge_action_available":available,"normal_speed_mps":gateway.player_state.run_speed_mps(gateway.server.max_speed_pct)}\n        request();began=Time.get_ticks_msec();phase=1\n    elif phase==1 and hidden():\n        report["original_handler_confirms_hidden"]=true\n        report["hidden_speed_mps"]=gateway.player_state.run_speed_mps(gateway.server.max_speed_pct)\n        if Time.get_ticks_msec()-began>=3000:request();phase=2\n    elif phase==2 and not hidden():\n        report["original_handler_confirms_visible"]=true\n        report["visible_speed_mps"]=gateway.player_state.run_speed_mps(gateway.server.max_speed_pct)\n        var folder:String=gateway.folder.path_join("../Reports/stealth_audit");DirAccess.make_dir_recursive_absolute(folder)\n        var f:=FileAccess.open(folder.path_join("probe.json"),FileAccess.WRITE);f.store_string(JSON.stringify(report));f.close();phase=99\n'
SOURCE=ROOT/'Godot'
D=ROOT/'StealthLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
BACKUP=ROOT/'Backups'/('StealthAudit_'+time.strftime('%Y%m%d-%H%M%S'));BACKUP.mkdir()
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
  (root/'Godot/stealth_probe.gd').write_text(STEALTH_PROBE,encoding='utf-8')
  (root/'Godot/gateway_main.gd').write_text('extends SceneTree\nfunc _initialize()->void:run.call_deferred()\nfunc run()->void:\n var folder:String=get_script().resource_path.get_base_dir()\n var gateway=load(folder.path_join("live_gateway.gd")).new();root.add_child(gateway)\n var probe=load(folder.path_join("stealth_probe.gd")).new();probe.gateway=gateway;root.add_child(probe)\n',encoding='utf-8')
  (root/'Reports/stealth_audit').mkdir(exist_ok=True);(root/'Reports/stealth_audit/probe.json').unlink(missing_ok=True)
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
 wait(lambda:(RUN/'Reports/stealth_audit/probe.json').exists(),'Original private Stealth request and return',35)
 probe=json.loads((RUN/'Reports/stealth_audit/probe.json').read_text())
 result['checks']['ordinary_nightshade_receives_original_specialization']=probe['server_spec_available']
 result['checks']['missing_bridge_action_reproduced']=not probe['bridge_action_available']
 result['checks']['original_type_zero_skill_request_hides']=probe['original_handler_confirms_hidden']
 result['checks']['original_hidden_speed_is_lower']=0<probe['hidden_speed_mps']<probe['normal_speed_mps']
 result['checks']['original_type_zero_skill_request_returns']=probe['original_handler_confirms_visible']
 result['checks']['original_visible_speed_restored']=abs(probe['visible_speed_mps']-probe['normal_speed_mps'])<.01
 (D/'original_probe.json').write_text(json.dumps(probe,indent=2),encoding='utf-8')
 (D/'active_snapshot.json').write_text(json.dumps(a.snapshot),encoding='utf-8')
 result['bug_reproduced']=True;result['passed']=all(result['checks'].values())
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
