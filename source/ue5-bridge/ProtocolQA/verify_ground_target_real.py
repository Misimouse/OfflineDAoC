"""Exercise original ground target and siege movement packets through a candidate bridge; restore private data and libraries."""
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3,shutil
import sys
source_qa=Path(os.environ.get("DAOC_BRIDGE_SOURCE_QA",str(ROOT.parent/"DAoC-Enhanced-Godot/source/ue5-bridge/ProtocolQA"))).resolve();assert (source_qa/"central_activation_receipts.py").is_file();sys.path.insert(0,str(source_qa))
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
SOURCE=source_qa.parent/'Godot'
dotnet=ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'
assert dotnet.is_file()
env.update(DOTNET_ROOT=str(dotnet.parent),DOTNET_ROOT_X64=str(dotnet.parent),PATH=str(dotnet.parent)+os.pathsep+env['PATH'])
D=ROOT/'GroundTargetLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
BACKUP=ROOT/'Backups'/('GroundTarget_'+time.strftime('%Y%m%d-%H%M%S'));BACKUP.mkdir()
config_backups=[];candidate_files=[];backed=False;nav_added=False
normal=verify_files(ROOT)
normal_paths=[ROOT/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll',INSTALL/'runtime/server/GameServer.dll',INSTALL/'runtime/server/lib/GameServer.dll']
normal_paths += [INSTALL/'new-client/godot/game/net/DaocClient.cs',INSTALL/'new-client/godot/.godot/mono/temp/bin/Debug/MMOEngine.dll',INSTALL/'new-client/godot/.godot/mono/temp/bin/Debug/MMOEngine.pdb']
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
 backend_path=ROOT/'GroundTargetLab/backend_verified.json';backend=json.loads(backend_path.read_text());assert backend['passed'] and backend['checks']>=8
 result['source_inputs'][str(backend_path)]=digest(backend_path)
 for name in ['MMOEngine.dll','MMOEngine.pdb']:
  target=RUN/'LobbyProject/.godot/mono/temp/bin/Debug'/name;origin=ROOT/'GroundTargetLab/BackendCandidate'/name
  assert target.resolve().is_relative_to(RUN) and origin.is_file()
  saved=BACKUP/('backend_'+name);shutil.copy2(target,saved);candidate_files.append((target,saved));shutil.copy2(origin,target)
  result['source_inputs'][str(origin)]=digest(origin)
 result['checks']['candidate_network_backend_loaded']=True
 for port in [10351,19737,19738]:
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):raise RuntimeError('Private QA port occupied')
  except (ConnectionRefusedError,socket.timeout):pass
 nav_source=INSTALL/'runtime/server/navmesh/zone207.nav';nav_target=SERVER/'pathing/zone207.nav';assert nav_source.is_file() and nav_target.resolve().is_relative_to(RUN)
 if not nav_target.exists():nav_target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(nav_source,nav_target);nav_added=True
 assert digest(nav_target)==digest(nav_source);result['source_inputs'][str(nav_source)]=digest(nav_source);result['checks']['original_connacht_navigation_private_only']=True
 with checked() as db:
  dest=sqlite3.connect(BACKUP/'before.sqlite3.db');db.backup(dest);dest.close();backed=True
  rows=db.execute("SELECT * FROM DOLCharacters WHERE Name IN ('Codexdruid','Codexfriend')").fetchall();assert len(rows)==2
  leader=dict(next(c for c in rows if c['Name']=='Codexdruid'))
  for c in rows:
   db.execute('UPDATE Account SET PrivLevel=?,Realm=3 WHERE Name=?',(1 if c['Name']=='Codexdruid' else 3,c['AccountName']))
  db.execute('UPDATE DOLCharacters SET Xpos=?,Ypos=?,Zpos=?,Region=? WHERE Name=?',(leader['Xpos'],leader['Ypos'],leader['Zpos'],leader['Region'],'Codexfriend'))
  result['checks']['ordinary_controller_and_fixture_gm']=db.execute('SELECT PrivLevel FROM Account WHERE Name=?',(leader['AccountName'],)).fetchone()[0]==1
 for n,root in enumerate([RUN,RUN/'friend-session']):
  assert root.resolve().is_relative_to(RUN)
  config=root/'bridge_config.json';config_backups.append((config,config.read_bytes()))
  cfg=json.loads(config.read_text());cfg['initial_spawn_m']=[(leader['Xpos']-35*8192)*.025,leader['Zpos']*.025,(leader['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
  for q in SOURCE.glob('*.gd'):shutil.copy2(q,root/'Godot'/q.name)
  # Decoded evidence stays only in this disposable client copy.
  q=root/'Godot/live_gateway.gd';text=q.read_text(encoding='utf-8-sig');text=text.replace('    siege.consume(kind,data,Time.get_ticks_msec())','    if kind.begins_with("siege_"):print("SIEGE_PACKET "+JSON.stringify({"kind":kind,"data":data}))\n    siege.consume(kind,data,Time.get_ticks_msec())',1);text=text.replace('func sync_ground_action_sight()->void:', 'func sync_ground_action_sight()->void:\n    print("GROUND_BACKEND_READY "+str(server.client.has_method("BridgeGroundTargetSight")))')
  q.write_text(text,encoding='utf-8')
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
 a.send('ui_bank',bar=0,bank=0);settle(.3)
 def control(peer):return peer.snapshot.get('siege',{})
 result['checks']['no_control_before_interaction']=all(not control(p).get('controlled') for p in peers)
 b.send('chat',text='/siegeweapon create ballista')
 def ballista():
  return next((row for row in a.snapshot.get('entities',[]) if 'ballista' in row.get('name','').lower()),None)
 wait(lambda:ballista() is not None,'Original GM fixture creates a visible ballista')
 row=ballista();a.send('interact',entity_id=row['id'])
 wait(lambda:control(a).get('controlled'),'Ordinary player receives server siege control')
 result['checks']['original_interface_has_oid_name_ammo']=control(a)['weapon']['oid']==int(row['id'].split(':')[1]) and 'ballista' in control(a)['weapon']['name'].lower() and isinstance(control(a)['weapon']['ammo'],list)
 result['checks']['independent_peer_has_no_control']=not control(b).get('controlled')
 start=list(row['position_m']);destination=list(start);destination[0]+=1.0
 a.send('ground_target',position_m=destination,visible=True)
 def ground():return a.snapshot.get('ground_target',{})
 wait(lambda:ground().get('has_point'),'Bridge forwards original ground point')
 result['checks']['point_uses_region_conversion']=ground()['position_m']==destination and not ground()['server_acknowledged']
 def moved():
  current=next((r for r in a.snapshot.get('entities',[]) if r['id']==row['id']),{})
  p=current.get('position_m',start);return sum((p[i]-start[i])**2 for i in range(3))>.0625
 wait(moved,'Original server moves controlled ballista toward ground target',12)
 result['checks']['original_ground_packet_moves_weapon']=moved()
 before=dict(ground());a.send('ground_target',position_m=[1e9,0,0],visible=True);settle(.3)
 result['checks']['invalid_point_does_not_replace_ground_target']=ground()['revision']==before['revision'] and ground()['position_m']==before['position_m']

 weapon=control(a)['weapon'];oid=weapon['oid']
 def send(command,**changes):
  args=dict(oid=oid,revision=control(a)['revision'],command=command,ammo=0);args.update(changes);a.send('siege_command',**args)
 for n in range(6):
  a.send('ground_target_sight',ground_target_revision=ground()['revision'],ground_target_in_view=True);settle(.3)
 result['checks']['stationary_geometry_keeps_ground_visibility_fresh']=ground().get('visible')
 a.send('ground_target_sight',ground_target_revision=ground()['revision'],ground_target_in_view=False)
 wait(lambda:not ground().get('visible'),'Independent geometry occlusion reaches ground state')
 send(5)
 wait(lambda:any('ground target is out of sight' in m.lower() for m in a.snapshot.get('messages',[])),'Original server refuses MOVE after ground occlusion')
 result['checks']['server_receives_independent_ground_visibility_bit']=True
 a.send('ground_target_sight',ground_target_revision=ground()['revision']-1,ground_target_in_view=True);settle(.3)
 result['checks']['stale_ground_geometry_refused']=not ground().get('visible')
 before=control(a).copy();send(8,oid=oid+1);settle(.4)
 result['checks']['wrong_weapon_does_not_release']=control(a).get('controlled')
 send(8,revision=control(a)['revision']-1);settle(.4)
 result['checks']['stale_window_does_not_release']=control(a).get('controlled')
 send(8)
 wait(lambda:not control(a).get('controlled'),'Original RELEASE closes the controlled siege window')
 result['checks']['server_release_authoritative']=not control(a).get('visible') and not control(a).get('weapon')
 a.send('interact',entity_id=row['id']);wait(lambda:control(a).get('controlled'),'Ordinary control can be acquired again')
 result['checks']['reacquire_after_release']=control(a)['weapon']['oid']==oid
 a.send('siege_hide',oid=oid,revision=control(a)['revision']);wait(lambda:not control(a).get('visible'),'Close hides the window')
 result['checks']['hide_preserves_server_control']=control(a).get('controlled')
 send(8);wait(lambda:not control(a).get('controlled'),'Release after hide still uses original server control')
 result['checks']['release_after_hide']=not control(a).get('controlled')
 (D/'active_snapshot.json').write_text(json.dumps(a.snapshot),encoding='utf-8')
 a.send('chat',text='/quit')
 wait(lambda:not a.snapshot.get('in_game',True) and a.snapshot.get('character_lobby',{}).get('ready'),'Original saved logout returns to character menu',90)
 result['checks']['menu_clears_control']=not control(a).get('controlled') and not control(a).get('visible')
 result['checks']['menu_clears_ground_target']=not ground().get('has_point') and not ground().get('visible')
 result['checks']['godot_public_network_sight_binding']= 'GROUND_BACKEND_READY true' in (D/'Codexdruid_client.log').read_text(encoding='utf-8')
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
 if nav_added:nav_target.unlink();result['private_navigation_restored']=True
 if backed:
  with checked() as db:
   src=sqlite3.connect(BACKUP/'before.sqlite3.db');src.backup(db);src.close()
  result['database_restored']=True
 result['private_server_restored']=bool(candidate_files)
 result['normal_shutdown']=bool(clients) and all(c.returncode==0 for c,_ in clients) and server is not None and server.returncode==0
 result['normal_runtime_unchanged']=all(digest(Path(p))==h for p,h in normal_hashes.items())
 result['passed']=result['passed'] and result['normal_shutdown'] and result.get('database_restored',False) and result['normal_runtime_unchanged'] and not result['errors'] and all(digest(Path(p))==h for p,h in result['source_inputs'].items())
 (D/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='source_inputs'}));assert result['passed']
