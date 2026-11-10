"""Exercise original ground target and siege movement packets through a candidate bridge; restore private data and libraries."""
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3,shutil
import sys
source_qa=Path(os.environ.get("DAOC_BRIDGE_SOURCE_QA",str(ROOT.parent/"DAoC-Enhanced-Godot/source/ue5-bridge/ProtocolQA"))).resolve();assert (source_qa/"central_activation_receipts.py").is_file();sys.path.insert(0,str(source_qa))
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
model_roundtrip=os.environ.get('DAOC_REMOTE_MODEL_ROUNDTRIP','0')=='1'
trade_probe=os.environ.get('DAOC_PLAYER_TRADE_PROBE','0')=='1'
assert not (model_roundtrip and trade_probe)
SOURCE=ROOT/'Godot' if model_roundtrip or trade_probe else source_qa.parent/'Godot'
dotnet=ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'
assert dotnet.is_file()
env.update(DOTNET_ROOT=str(dotnet.parent),DOTNET_ROOT_X64=str(dotnet.parent),PATH=str(dotnet.parent)+os.pathsep+env['PATH'])
D=ROOT/('PlayerTradeLab/RealProtocol' if trade_probe else 'RemoteModelRoundtripLab/RealProtocol' if model_roundtrip else 'RemotePlayerLab/RealProtocol')/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
BACKUP=ROOT/'Backups'/('RemotePlayer_'+time.strftime('%Y%m%d-%H%M%S'));BACKUP.mkdir()
config_backups=[];candidate_files=[];backed=False;nav_added=False
normal=verify_files(ROOT)
normal_paths=[ROOT/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll',INSTALL/'runtime/server/GameServer.dll',INSTALL/'runtime/server/lib/GameServer.dll']
normal_paths += [ROOT/'models.json',INSTALL/'new-client/godot/game/net/DaocClient.cs',INSTALL/'new-client/godot/.godot/mono/temp/bin/Debug/MMOEngine.dll',INSTALL/'new-client/godot/.godot/mono/temp/bin/Debug/MMOEngine.pdb']
normal_hashes={str(p):digest(p) for p in normal_paths}
def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row;assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name;return db
def persist_recovery():
 files=[dict(target=str(t),backup=str(b),sha256=digest(b)) for t,b in candidate_files]
 for n,(target,raw) in enumerate(config_backups):
  saved=BACKUP/('config_'+str(n));saved.write_bytes(raw);files.append(dict(target=str(target),backup=str(saved),sha256=digest(saved)))
 recovery=dict(phase='running',private_run=str(RUN),database=str(DB),database_backup=str(BACKUP/'before.sqlite3.db') if backed else None,files=files,private_navigation_added=nav_added,normal_hashes=normal_hashes)
 (D/'recovery.json').write_text(json.dumps(recovery,indent=2))
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
model_source=ROOT/'models.json' if model_roundtrip or trade_probe else ROOT/'SiegeWorldLab/models_candidate.json'
result['source_inputs'][str(model_source)]=digest(model_source)
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
 backend_path=ROOT/'RemotePlayerLab/backend_verified.json';backend=json.loads(backend_path.read_text());assert backend['passed'] and backend['checks']>=8
 if trade_probe:
  result['source_inputs'][str(source_qa/'player_trade_wire_case.py')]=digest(source_qa/'player_trade_wire_case.py')
  result['source_inputs'][str(Path(__file__).resolve())]=digest(Path(__file__).resolve())
  backend_path=Path(os.environ['DAOC_PLAYER_TRADE_BACKEND_PROOF']).resolve();assert backend_path.is_relative_to(ROOT/'PlayerTradeLab/WireCodec')
  backend=json.loads(backend_path.read_text());assert backend['passed'] and backend['checks']>=146 and backend['candidate_dispatch_enabled']
  assert digest(Path(backend['candidate_backend']))==backend['candidate_backend_sha256']
  assert all(digest(Path(p))==sha for p,sha in backend['source_inputs'].items())
  result['source_inputs'][str(backend_path)]=digest(backend_path)
  result.update(direct_transport_probe=True,production_gateway_guards_tested=False,ui_installed=False)
 if not model_roundtrip:result['source_inputs'][str(backend_path)]=digest(backend_path)
 for name in ['MMOEngine.dll','MMOEngine.pdb']:
  target=RUN/'LobbyProject/.godot/mono/temp/bin/Debug'/name;origin=INSTALL/'new-client/godot/.godot/mono/temp/bin/Debug'/name if model_roundtrip else ROOT/'RemotePlayerLab/BackendCandidate'/name
  if trade_probe:origin=Path(backend['candidate_backend']).parent/name
  assert target.resolve().is_relative_to(RUN) and origin.is_file()
  saved=BACKUP/('backend_'+name);shutil.copy2(target,saved);candidate_files.append((target,saved));persist_recovery();shutil.copy2(origin,target)
  result['source_inputs'][str(origin)]=digest(origin)
 result['checks']['candidate_network_backend_loaded']=True
 for port in [10351,19737,19738]:
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):raise RuntimeError('Private QA port occupied')
  except (ConnectionRefusedError,socket.timeout):pass
 nav_source=INSTALL/'runtime/server/navmesh/zone207.nav';nav_target=SERVER/'pathing/zone207.nav';assert nav_source.is_file() and nav_target.resolve().is_relative_to(RUN)
 if not nav_target.exists():nav_added=True;persist_recovery();nav_target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(nav_source,nav_target)
 assert digest(nav_target)==digest(nav_source);result['source_inputs'][str(nav_source)]=digest(nav_source);result['checks']['original_connacht_navigation_private_only']=True
 with checked() as db:
  dest=sqlite3.connect(BACKUP/'before.sqlite3.db');db.backup(dest);dest.close();backed=True;persist_recovery()
  rows=db.execute("SELECT * FROM DOLCharacters WHERE Name IN ('Codexdruid','Codexfriend')").fetchall();assert len(rows)==2
  leader=dict(next(c for c in rows if c['Name']=='Codexdruid'))
  if model_roundtrip:
   from prepare_combined_expansion_data import apply_marked
   proposal=ROOT/'Reports/combined_expansions/data_integration/proposal.json'
   result['source_inputs'][str(proposal)]=digest(proposal)
   result['preloaded_combined_data']=apply_marked(db,proposal,RUN.name,ROOT)
   db.execute("UPDATE DOLCharacters SET Class=39,Level=5,Experience=0,SerializedSpecs='',Gender=1,Race=9,CreationModel=310,CurrentModel=310,Health=200,Mana=100,DeathTime=0,HasGravestone=0,DisabledSpells='',DisabledAbilities='' WHERE Name='Codexdruid'")
  for c in rows:
   db.execute('UPDATE Account SET PrivLevel=?,Realm=3 WHERE Name=?',(1,c['AccountName']))
  db.execute('UPDATE DOLCharacters SET Xpos=?,Ypos=?,Zpos=?,Region=? WHERE Name=?',(leader['Xpos'],leader['Ypos'],leader['Zpos'],leader['Region'],'Codexfriend'))
  result['checks']['both_players_ordinary']=all(db.execute('SELECT PrivLevel FROM Account WHERE Name=?',(c['AccountName'],)).fetchone()[0]==1 for c in rows)
  if trade_probe:
   from player_trade_wire_case import prepare
   prepare(db,rows,leader)
 for n,root in enumerate([RUN,RUN/'friend-session']):
  assert root.resolve().is_relative_to(RUN)
  model_path=root/'models.json';assert model_path.resolve().is_relative_to(RUN) and not model_path.is_symlink();config_backups.append((model_path,model_path.read_bytes()));persist_recovery();shutil.copy2(model_source,model_path)
  config=root/'bridge_config.json';config_backups.append((config,config.read_bytes()));persist_recovery()
  cfg=json.loads(config.read_text());cfg['initial_spawn_m']=[(leader['Xpos']-35*8192)*.025,leader['Zpos']*.025,(leader['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
  for q in SOURCE.glob('*.gd'):shutil.copy2(q,root/'Godot'/q.name)
  # Decoded evidence stays only in this disposable client copy.
  q=root/'Godot/live_gateway.gd';text=q.read_text(encoding='utf-8-sig');text=text.replace('    siege.consume(kind,data,Time.get_ticks_msec())','    if kind.begins_with("siege_"):print("SIEGE_PACKET "+JSON.stringify({"kind":kind,"data":data}))\n    siege.consume(kind,data,Time.get_ticks_msec())',1);text=text.replace('func sync_ground_action_sight()->void:', 'func sync_ground_action_sight()->void:\n    print("GROUND_BACKEND_READY "+str(server.client.has_method("BridgeGroundTargetSight")))')
  text=text.replace('        server.client.connect("Packet",Callable(player_models,"consume_raw"))','        server.client.connect("Packet",Callable(player_models,"consume_raw"))\n        server.client.connect("Packet",func(code,data):\n            if int(code)==169:print("RAW_PLAYER_POSITION "+str(data.size())+" "+data.hex_encode()))')
  text=text.replace('    realm_war.consume(kind,data)','    if kind=="player_move":print("REMOTE_PACKET "+JSON.stringify(data))\n    realm_war.consume(kind,data)')
  if trade_probe:
   text=text.replace('extends Node','extends Node\nvar qa_player_trade:Dictionary={}',1)
   text=text.replace('    server.world.connect(world_event)','    server.world.connect(world_event)\n    print("QA_TRADE_CODEC_PRESENT "+str(server.client.has_method("PlayerTrade")))\n    server.client.connect("World",func(kind,data):\n        if kind=="player_trade":print("QA_TRADE_DECODED "+JSON.stringify(data)))')
   text=text.replace('if int(code)==169:print("RAW_PLAYER_POSITION "+str(data.size())+" "+data.hex_encode())','if int(code)==169:print("RAW_PLAYER_POSITION "+str(data.size())+" "+data.hex_encode())\n            if int(code)==234:print("RAW_PLAYER_TRADE "+data.hex_encode())')
   text=text.replace('func world_event(kind:String,data:Dictionary)->void:', 'func world_event(kind:String,data:Dictionary)->void:\n    if kind=="player_trade":\n        data["qa_revision"]=int(qa_player_trade.get("qa_revision",0))+1\n        qa_player_trade=data.duplicate(true)')
   text=text.replace('        transport.snapshot_metadata["classic_ui"]=classic_ui.snapshot()','        transport.snapshot_metadata["qa_player_trade"]=qa_player_trade.duplicate(true)\n        transport.snapshot_metadata["classic_ui"]=classic_ui.snapshot()')
   hook='''    if String(value.get("action",""))=="chat" and String(value.get("text","")).begins_with("/qa-player-trade "):
        var request:Dictionary=JSON.parse_string(String(value.text).trim_prefix("/qa-player-trade "))
        print("QA_TRADE_COMMAND "+JSON.stringify(request))
        if request.get("op","")=="open":server.client.MoveItem(int(request.slot),1000+int(request.oid),1)
        else:server.client.PlayerTrade(int(request.action),PackedInt32Array(request.get("slots",[])),PackedInt32Array(request.get("money",[])))
        return
'''
   text=text.replace('func command(value:Dictionary)->void:', 'func command(value:Dictionary)->void:\n'+hook)
  q.write_text(text,encoding='utf-8')
  debug_adapter=root/'Godot/decoded_world_adapter.gd';ds=debug_adapter.read_text(encoding='utf-8-sig');ds=ds.replace('    if not oid_to_id.has(oid):_request_missing(oid);return','    if not oid_to_id.has(oid):\n        print("REMOTE_UNKNOWN "+JSON.stringify({"oid":oid,"local":local_oid,"non_living":non_living.has(oid),"requested":requested.has(oid)}))\n        _request_missing(oid);return');debug_adapter.write_text(ds,encoding='utf-8')
  q=root/'Godot/visual_bridge.gd';vt=q.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = '+str(19737+n))
  if trade_probe:vt=vt.replace('["character",','["qa_player_trade","character",',1)
  q.write_text(vt,encoding='utf-8')
 candidate_root=ROOT/'GuildWindowLab/ServerCandidate';candidate=json.loads((candidate_root/'build_receipt.json').read_text());assert candidate['passed']
 for folder in [SERVER,SERVER/'lib',SERVER/'win-x64']:
  for name,expected in candidate['binaries_sha256'].items():
   target=folder/name
   if not target.exists():continue
   assert target.resolve().is_relative_to(RUN);origin=Path(candidate['libraries'])/name;assert digest(origin)==expected
   saved=BACKUP/('server_'+str(len(candidate_files))+'_'+name);shutil.copy2(target,saved);candidate_files.append((target,saved));persist_recovery();shutil.copy2(origin,target)
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
 if trade_probe:
  from player_trade_wire_case import run
  run(a,b,wait,settle,result,checked,D)
 else:
  # Headless peers have no native frame pump: send each original initial position.
  for peer in [a,b]:
   local=next(r for r in peer.snapshot.get('entities',[]) if r['id']=='player:local')
   peer.send('move',position_m=local['position_m'],forward_xz=[0,1],speed_mps=0.0,swimming=False,on_ground=True,vertical_speed_mps=0)
  settle(.5)
  def remote(peer,name):return next((r for r in peer.snapshot.get('entities',[]) if r.get('kind')=='player' and r.get('name','').lower()==name.lower()),None)
  wait(lambda:remote(b,'Codexdruid') is not None and remote(a,'Codexfriend') is not None,'Two actual player bodies delivered',20)
  first=remote(b,'Codexdruid');second=remote(a,'Codexfriend');id_a=first['id'];id_b=second['id']
  result['checks']['distinct_original_sessions']=first['session_id']>0 and second['session_id']>0 and first['session_id']!=second['session_id']
  result['checks']['both_realm_identity']=first['realm']==3 and second['realm']==3
  start=list(first['position_m']);point=list(start)
  for n in range(8):
   point[0]+=.25;a.send('move',position_m=point,forward_xz=[1,0],speed_mps=2.0,swimming=False,on_ground=True,vertical_speed_mps=0);settle(.15)
  wait(lambda:remote(b,'Codexdruid').get('motion',{}).get('source_packet')=='player_position1127' and remote(b,'Codexdruid')['position_m'][0]>start[0]+1.5,'Production0xA9 reaches independent observer',15)
  current=remote(b,'Codexdruid');result['checks']['absolute_region_coordinates']=all(abs(current['position_m'][i]-point[i])<.051 for i in range(3))
  result['checks']['original_speed_units']=abs(current['speed_mps']-2.0)<.001
  result['checks']['original_heading']=abs(current['forward_xz'][0]-1)<.001 and abs(current['forward_xz'][1])<.001
  result['checks']['remote_movement_not_npc']=current['kind']=='player' and current['id']==id_a and current['motion'].get('source_packet')=='player_position1127'
  result['checks']['no_invented_destination']=not current['motion'].get('destination_m')
  seqs=[r['motion']['seq'] for snapshot in b.trace for r in snapshot.get('entities',[]) if r.get('id')==id_a and r.get('motion',{}).get('source_packet')=='player_position1127'];result['checks']['snapshot_repeat_stable']=any(seqs[i]==seqs[i-1] for i in range(1,len(seqs)))
  a.send('move',position_m=point,forward_xz=[1,0],speed_mps=0.0,swimming=False,on_ground=True,vertical_speed_mps=0)
  wait(lambda:remote(b,'Codexdruid')['speed_mps']==0,'Remote original stop',8)
  result['checks']['remote_stop']=remote(b,'Codexdruid')['state']=='idle'
  a.send('player_sit',on=True,player_generation=a.snapshot['player_status']['generation'])
  wait(lambda:a.snapshot.get('player_status',{}).get('vitals',{}).get('sitting'),'Original sit confirmed',12)
  a.send('move',position_m=point,forward_xz=[1,0],speed_mps=0.0,swimming=False,on_ground=True,vertical_speed_mps=0)
  wait(lambda:remote(b,'Codexdruid').get('remote_sitting'),'Original sitting state reaches observer',12)
  result['checks']['remote_sitting']=remote(b,'Codexdruid')['state']=='sit_idle' and not remote(b,'Codexdruid')['remote_swimming']
  a.send('player_sit',on=False,player_generation=a.snapshot['player_status']['generation']);wait(lambda:not a.snapshot.get('player_status',{}).get('vitals',{}).get('sitting',True),'Original stand confirmed',12)
  a.send('move',position_m=point,forward_xz=[1,0],speed_mps=0.0,swimming=False,on_ground=True,vertical_speed_mps=0)
  wait(lambda:not remote(b,'Codexdruid').get('remote_sitting',True),'Standing reaches observer',8)
  result['checks']['remote_stand']=remote(b,'Codexdruid')['state']=='idle'
  other_start=list(second['position_m']);other=list(other_start);other[2]+=.5;b.send('move',position_m=other,forward_xz=[0,1],speed_mps=1.0,swimming=False,on_ground=True,vertical_speed_mps=0)
  wait(lambda:remote(a,'Codexfriend')['position_m'][2]>other_start[2]+.3,'Reverse direction reaches first peer',8)
  result['checks']['bidirectional_identity']=remote(a,'Codexfriend')['id']==id_b and remote(b,'Codexdruid')['id']==id_a
  result['checks']['independent_speed']=remote(a,'Codexfriend')['speed_mps']==1.0 and remote(b,'Codexdruid')['speed_mps']==0.0
  (D/'active_snapshot.json').write_text(json.dumps(b.snapshot),encoding='utf-8')
  if model_roundtrip:
   # Both clients remain ordinary. The original cone spell triggers the
   # server's real Bainshee form timer; never inject a synthetic model packet.
   for peer in peers:
    local=next(r for r in peer.snapshot['entities'] if r['id']=='player:local')
    peer.send('move',position_m=local['position_m'],forward_xz=[0,1],speed_mps=0.0,swimming=False,on_ground=True,vertical_speed_mps=0)
   settle(1)
   original=json.loads(json.dumps(remote(b,'Codexdruid')))
   entry=next(e for e in a.snapshot['classic_ui']['entries'] if e.get('kind')=='spell' and e.get('name')=="Bawler's Bruise")
   a.send('ui_use',entry_id=entry['id'],entry_token=entry['token'])
   wait(lambda:remote(b,'Codexdruid').get('model_id')==1883,'Original offensive cast reaches ordinary observer as Bainshee form',25)
   transformed=json.loads(json.dumps(remote(b,'Codexdruid')));started=time.monotonic()
   result['checks']['original_remote_bainshee_form']=transformed['model_id']==1883
   result['checks']['remote_morph_retains_size']=transformed['size']==original['size'] and transformed['size']>0
   result['checks']['remote_morph_retains_equipment']=transformed.get('equipment')==original.get('equipment')
   wait(lambda:remote(b,'Codexdruid').get('model_id')==original['model_id'],'Original timer returns remote race body',45)
   restored=json.loads(json.dumps(remote(b,'Codexdruid')))
   result['checks']['remote_form_timer']=25<=time.monotonic()-started<=40
   result['checks']['remote_restore_size']=restored['size']==original['size']
   result['checks']['remote_restore_equipment']=restored.get('equipment')==original.get('equipment')
   result['checks']['remote_identity_stable']=restored['id']==original['id'] and restored['session_id']==original['session_id']
   (D/'remote_form_trace.json').write_text(json.dumps(dict(original=original,transformed=transformed,restored=restored),indent=2))
  a.send('chat',text='/quit');wait(lambda:not a.snapshot.get('in_game',True) and a.snapshot.get('character_lobby',{}).get('ready'),'Original saved logout returns to menu',90)
  wait(lambda:remote(b,'Codexdruid') is None,'Original removal clears other player',15)
  result['checks']['remote_logout_removes_identity']=all(r['id']!=id_a for r in b.snapshot.get('entities',[]))
  result['checks']['local_menu_clears_world']=not any(r.get('kind')=='player' for r in a.snapshot.get('entities',[]))
 result['passed']=all(result['checks'].values())
except Exception:result['errors'].append(traceback.format_exc())
finally:
 for peer in peers:
  if peer.snapshot.get('in_game'):
   try:
    local=next(r for r in peer.snapshot.get('entities',[]) if r['id']=='player:local')
    peer.send('move',position_m=local['position_m'],forward_xz=[0,1],speed_mps=0.0,swimming=False,on_ground=True,vertical_speed_mps=0)
   except (OSError,StopIteration):pass
 if peers:
  try:settle(.4)
  except (OSError,RuntimeError):pass
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
 persist_recovery();recovered=json.loads((D/'recovery.json').read_text());recovered['phase']='restored';(D/'recovery.json').write_text(json.dumps(recovered,indent=2))
 (D/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='source_inputs'}));assert result['passed']
