"""Exercise original item drop/create/target/pickup with an ordinary disposable account; restore private data."""
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3,shutil
import sys
source_qa=Path(os.environ.get("DAOC_BRIDGE_SOURCE_QA",str(ROOT.parent/"DAoC-Enhanced-Godot/source/ue5-bridge/ProtocolQA"))).resolve();assert (source_qa/"central_activation_receipts.py").is_file();sys.path.insert(0,str(source_qa))
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
SOURCE=source_qa.parent/'Godot'
D=ROOT/'GroundObjectRuntimeLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
BACKUP=ROOT/'Backups'/('GroundObjectPickup_'+time.strftime('%Y%m%d-%H%M%S'));BACKUP.mkdir()
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
  leader=db.execute("SELECT * FROM DOLCharacters WHERE Name='Codexdruid'").fetchone();assert leader
  db.execute('UPDATE Account SET PrivLevel=1,Realm=3 WHERE Name=?',(leader['AccountName'],))
  db.execute('UPDATE DOLCharacters SET HCFlag=0 WHERE DOLCharacters_ID=?',(leader['DOLCharacters_ID'],))
  assert db.execute('SELECT PrivLevel FROM Account WHERE Name=?',(leader['AccountName'],)).fetchone()[0]==1
  result['checks']['ordinary_account_only']=True
  # A fixture item exists only inside the marked, backed-up disposable database.
  item=dict(db.execute('SELECT * FROM Inventory WHERE OwnerID=? AND SlotPosition=40',(leader['DOLCharacters_ID'],)).fetchone());assert item
  assert not db.execute('SELECT 1 FROM Inventory WHERE OwnerID=? AND SlotPosition=41',(leader['DOLCharacters_ID'],)).fetchone()
  import uuid
  item.update(Inventory_ID=str(uuid.uuid4()),ITemplate_Id='Adder_Fang',UTemplate_Id=None,SlotPosition=41,Count=1)
  db.execute('INSERT INTO Inventory ('+','.join(item)+') VALUES ('+','.join('?' for _ in item)+')',list(item.values()))
  assert db.execute("SELECT IsDropable FROM ItemTemplate WHERE Id_nb='Adder_Fang'").fetchone()[0]==1
 for root in [RUN]:
  assert root.resolve().is_relative_to(RUN)
  config=root/'bridge_config.json';config_backups.append((config,config.read_bytes()))
  cfg=json.loads(config.read_text());cfg['initial_spawn_m']=[(leader['Xpos']-35*8192)*.025,leader['Zpos']*.025,(leader['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
  for q in SOURCE.glob('*.gd'):shutil.copy2(q,root/'Godot'/q.name)
  q=root/'Godot/visual_bridge.gd';q.write_text(q.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = 19737').replace('"player_sprint","target_object"','"qa_ground_drop","player_sprint","target_object"'),encoding='utf-8')
  # Test-only dispatch calls the unchanged original C# MoveItem. It is never installed.
  wrapper='extends "live_gateway.gd"\nfunc command(value:Dictionary)->void:\n    if value.get("action","")=="qa_ground_drop":\n        if server.playing and not leaving:server.client.call("MoveItem",41,1,1)\n        return\n    super.command(value)\n'
  (root/'Godot/private_ground_gateway.gd').write_text(wrapper,encoding='utf-8')
  (root/'Godot/private_ground_main.gd').write_text('extends SceneTree\nfunc _initialize()->void:run.call_deferred()\nfunc run()->void:\n    var gateway=load(get_script().resource_path.get_base_dir().path_join("private_ground_gateway.gd")).new();root.add_child(gateway)\n',encoding='utf-8')
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
 for character,suffix,root,port in [('Codexdruid','',RUN,19737)]:
  account='codexqa'+hashlib.sha256((RUN.name+suffix).encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name+suffix).encode()).hexdigest()[:24]
  ce=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'],APPDATA=str(root/'appdata'))
  log=(D/(character+'_client.log')).open('w',encoding='utf-8');handles.append(log);(root/'Reports/live/logout.request').unlink(missing_ok=True)
  client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(root/'Godot/private_ground_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character='+character,'--bridge-ground-objects'],cwd=root,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  clients.append((client,root));peers.append(Peer(port))
 a=peers[0]
 def items():return a.snapshot.get('inventory',{}).get('items',[])
 def count():return sum(int(i.get('count',1)) for i in items() if i.get('name')=='Adder Fang')
 def objects():return a.snapshot.get('world_objects',{}).get('objects',[])
 def bag():return next((o for o in objects() if o.get('name')=='Adder Fang'),None)
 def cmd(action,row,**extra):a.send(action,entity_id=row['id'],object_token=row['object_token'],world_generation=row['world_generation'],**extra)
 wait(lambda:a.snapshot.get('classic_ui',{}).get('skills_ready') and count()==1,'Ordinary player and fixture item ready',40)
 a.send('qa_ground_drop');wait(lambda:count()==0 and bag() is not None,'Original drop and ObjectCreate')
 first=dict(bag());result['checks']['server_drop_creates_ground_identity']=first['kind']=='object' and first['model_id']==488
 cmd('target_object',first);wait(lambda:a.snapshot.get('interaction',{}).get('target',{}).get('id')==first['id'],'Ground target selected');settle(.5)
 result['checks']['click_selects_without_pickup']=count()==0 and bag() is not None
 bad=dict(first,object_token='stale');cmd('get_object',bad);settle(.5);result['checks']['stale_identity_refused']=count()==0 and bag() is not None
 bad=dict(first,world_generation=first['world_generation']-1);cmd('get_object',bad);settle(.5);result['checks']['stale_generation_refused']=count()==0 and bag() is not None
 cmd('get_object',first);wait(lambda:count()==1 and bag() is None,'Original pickup inventory and delete confirmation');result['checks']['original_pickup_returns_one_item']=True
 wait(lambda:not a.snapshot.get('interaction',{}).get('target'),'Deleted target cleared');result['checks']['confirmed_delete_clears_selection']=True
 cmd('get_object',first);settle(.5);result['checks']['repeated_pickup_cannot_duplicate']=count()==1
 # The server may reuse an OID; current selection and instance token must still change.
 inv=next(i for i in items() if i.get('name')=='Adder Fang');result['checks']['original_item_returns_to_backpack']=40<=int(inv['slot'])<=79
 if int(inv['slot'])!=41:
  a.send('inventory_move',slot=int(inv['slot']),to_slot=41,item_token=inv['token'],inventory_revision=a.snapshot['inventory']['state_revision'])
  wait(lambda:any(i.get('name')=='Adder Fang' and i.get('slot')==41 for i in items()),'Fixture restored to drop slot')
 a.send('qa_ground_drop');wait(lambda:count()==0 and bag() is not None,'Second actual drop');second=dict(bag());result['checks']['new_instance_has_new_token']=second['object_token']!=first['object_token']
 cmd('get_object',first);settle(.5);result['checks']['old_instance_does_not_pick_new_bag']=count()==0 and bag() is not None
 cmd('target_object',second);wait(lambda:a.snapshot.get('interaction',{}).get('target',{}).get('id')==second['id'],'Second bag selected');cmd('get_object',second)
 wait(lambda:count()==1 and bag() is None,'Second ordinary pickup');result['checks']['repeated_drop_pickup_roundtrip']=True
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
