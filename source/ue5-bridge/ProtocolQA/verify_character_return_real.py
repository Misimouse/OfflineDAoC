"""Server-confirmed logout, clean selection and same-connection reentry; disposable DB only."""
from qa_runtime import *
import sqlite3,subprocess,socket,time,hashlib,shutil,traceback

D=ROOT/'Reports/character_return';D.mkdir(exist_ok=True)
SOURCE=Path(os.environ.get('DAOC_BRIDGE_QA_GODOT',str(ROOT/'Godot')))
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[]}
server=client=sock=None;logs=[];session='';snapshot={};buffer=b'';serial=0;backed=False
backup=ROOT/'Backups'/('CharacterReturnQA_'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir()
config=RUN/'bridge_config.json';config_bytes=config.read_bytes()
def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row;assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name;return db
def update(db,table,keyfield,key,values):db.execute('UPDATE '+table+' SET '+','.join('"'+k+'"=?' for k in values)+' WHERE "'+keyfield+'"=?',list(values.values())+[key])
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='cloak:'+str(serial),action=action,**values))+'\n').encode())
def pump():
 global session,snapshot,buffer
 try:data=sock.recv(1048576)
 except socket.timeout:return
 if not data:raise RuntimeError('Private character bridge closed')
 buffer+=data
 while b'\n' in buffer:
  line,buffer=buffer.split(b'\n',1);v=json.loads(line)
  if v.get('type')=='hello':session=v['session']
  if v.get('type')=='snapshot':snapshot=v
def wait(test,label,seconds=30):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  pump()
  if test():return
 raise RuntimeError(label+'; inventory='+str(inv().get('feedback'))+'; flags='+str(gear()))
def settle(seconds=.8):
 end=time.monotonic()+seconds
 while time.monotonic()<end:pump()
def inv():return snapshot.get('inventory',{})
def gear():return inv().get('gear',{})
def item(slot):return next((i for i in inv().get('items',[]) if i['slot']==slot),None)
try:
 for port in [10351,19737]:
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):raise RuntimeError('Private QA port already occupied')
  except (ConnectionRefusedError,socket.timeout):pass
 with checked() as db:
  dest=sqlite3.connect(backup/'before.sqlite3.db');db.backup(dest);dest.close();backed=True
  char=db.execute("SELECT * FROM DOLCharacters WHERE Name='Codexdruid'").fetchone();assert char
  update(db,'Account','Name',char['AccountName'],{'PrivLevel':3,'Realm':3})
  update(db,'DOLCharacters','DOLCharacters_ID',char['DOLCharacters_ID'],{'Class':53,'Level':1,'Experience':0,'SerializedSpecs':'','Health':10})
 cfg=json.loads(config_bytes);cfg['initial_spawn_m']=[(char['Xpos']-35*8192)*.025,char['Zpos']*.025,(char['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
 for p in SOURCE.glob('*.gd'):shutil.copy2(p,RUN/'Godot'/p.name)
 p=RUN/'Godot/visual_bridge.gd';p.write_text(p.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = 19737'),encoding='utf-8')
 log=(D/'character_return_server.log').open('w',encoding='utf-8');logs.append(log)
 server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+40
 while time.monotonic()<end:
  try:
   with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Private QA server unavailable')
 game=INSTALL/'new-client';sdk=ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64'
 account='codexqa'+hashlib.sha256(RUN.name.encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name).encode()).hexdigest()[:24]
 ce=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'])
 (RUN/'Reports/live/logout.request').unlink(missing_ok=True)
 log=(D/'character_return_client.log').open('w',encoding='utf-8');logs.append(log)
 client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character=Codexdruid'],cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+50
 while time.monotonic()<end:
  try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);sock.settimeout(.1);break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Private character bridge unavailable')
 wait(lambda:snapshot.get('classic_ui',{}).get('skills_ready') and snapshot.get('player_status',{}).get('ready'),'Initial Naturalist world ready');settle(2)
 send('chat',text='/quit')
 wait(lambda:not snapshot.get('in_game') and snapshot.get('character_lobby',{}).get('ready'),'Saved quit returns selection',45)
 lobby=snapshot['character_lobby'];assert lobby['enabled'] and lobby['characters']
 result['checks']['quit_stays_connected']=True;result['roster_classes']=[dict(name=c['name'],class_name=c['class_name'],level=c['level']) for c in lobby['characters']]
 assert not snapshot.get('entities');result['checks']['old_world_cleared']=True
 send('character_enter',name='Codexdruid',lobby_revision=lobby['revision'])
 wait(lambda:snapshot.get('in_game') and snapshot.get('player_status',{}).get('ready') and snapshot.get('classic_ui',{}).get('skills_ready'),'Re-enter from same character screen',30)
 result['checks']['same_connection_reentry']=True
 (D/'returned_snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8');result['passed']=True

except Exception:
 result['errors'].append(traceback.format_exc());(D/'character_return_failed.json').write_text(json.dumps(snapshot),encoding='utf-8')
finally:
 if sock and session:
  try:send('logout')
  except OSError:pass
 if client and client.poll() is None:
  (RUN/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
  try:client.wait(timeout=90)
  except subprocess.TimeoutExpired:client.kill();client.wait();result['errors'].append('Private character client forced stop')
 if sock:sock.close()
 if server and server.poll() is None:
  server.stdin.write('exit\n');server.stdin.flush()
  try:server.wait(timeout=45)
  except subprocess.TimeoutExpired:server.kill();server.wait();result['errors'].append('Private server forced stop')
 for log in logs:log.close()
 if backed:
  assert DB.is_relative_to(RUN) and RUN.is_relative_to(ROOT/'ProtocolQA')
  with checked() as dst:
   src=sqlite3.connect(backup/'before.sqlite3.db');src.backup(dst);src.close()
  config.write_bytes(config_bytes);result['database_restored']=True
 result['normal_shutdown']=bool(client and server and client.returncode==0 and server.returncode==0)
 result['passed']=result['passed'] and result['normal_shutdown'] and not result['errors']
 (D/'quit_protocol.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));assert result['passed']
