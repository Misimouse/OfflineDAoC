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
peers=[];clients=[];handles=[];server=None
result={'passed':False,'real_protocol':True,'disposable_only':True,'errors':[]}
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
 with sqlite3.connect(DB) as db:
  assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name
  friend_account='codexqa'+hashlib.sha256((RUN.name+':friend').encode()).hexdigest()[:10]
  assert db.execute('SELECT COUNT(*) FROM Account').fetchone()[0]==2
  db.execute('UPDATE Account SET PrivLevel=1, Realm=3 WHERE Name=?',(friend_account,))
 output=(RUN/'chat_server.log').open('w',encoding='utf-8');handles.append(output)
 server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=output,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 deadline=time.monotonic()+30
 while time.monotonic()<deadline:
  try:
   with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Isolated server unavailable')
 time.sleep(2) # TCP binds before the original server opens logins.
 game=Path(str(INSTALL / 'new-client'));sdk=Path(str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64'))
 for character,suffix,root,port in [('Codexdruid','',RUN,19737),('Codexfriend',':friend',RUN/'friend-session',19738)]:
  account='codexqa'+hashlib.sha256((RUN.name+suffix).encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name+suffix).encode()).hexdigest()[:24]
  client_env=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'],APPDATA=str(root/'appdata'))
  log=(root/'chat_client.log').open('w',encoding='utf-8');handles.append(log)
  request=root/'Reports/live/logout.request'
  if request.exists():request.unlink()
  client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(game/'godot'),'--script',str(root/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character='+character],cwd=root,env=client_env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  clients.append((client,root));peers.append(Peer(port))
 wait(lambda:all(p.snapshot.get('classic_ui',{}).get('skills_ready') for p in peers),'Both actual players ready')
 a,b=peers
 for peer in peers:peer.send('chat',text='/gmstealth off')
 wait(lambda:any(e.get('name')=='Codexfriend' for e in a.snapshot.get('entities',[])),'Friend is a real world entity')
 target=next(e for e in a.snapshot['entities'] if e.get('name')=='Codexfriend');a.send('target',entity_id=target['id'])
 wait(lambda:a.snapshot.get('interaction',{}).get('target',{}).get('id')==target['id'],'Selected invitation target')
 def invite():
  a.send('group_invite',entity_id=target['id'])
  wait(lambda:bool(b.snapshot.get('interaction',{}).get('dialogs')) or all(len(p.party().get('members',[]))==2 for p in peers),'Original invitation or GM group add')
  if b.snapshot.get('interaction',{}).get('dialogs'):
   dialog=b.snapshot['interaction']['dialogs'][0];b.send('dialog_response',dialog_id=dialog['id'],answer=1)
  wait(lambda:all(len(p.party().get('members',[]))==2 for p in peers),'Both authoritative rosters')
 invite()
 def entries(peer):return peer.snapshot.get('chat',{}).get('entries',[])
 def received(peer,marker,kind):return any(marker in e.get('text','') and e.get('kind')==kind and e.get('source')=='server' for e in entries(peer))
 before=[p.snapshot.get('inventory',{}).get('items',[]) for p in peers]
 a.send('chat',text='/g QA_GROUP <literal> & [keyword]')
 wait(lambda:all(received(p,'QA_GROUP <literal> & [keyword]','group') for p in peers),'Group channel delivered with literal text')
 b.send('chat',text='/send Codexdruid QA_PRIVATE <literal> & [keyword]')
 wait(lambda:received(a,'QA_PRIVATE <literal> & [keyword]','send'),'Private message received')
 a.send('chat',text='/gu QA_GUILD <literal> & [keyword]')
 wait(lambda:all(received(p,'QA_GUILD <literal> & [keyword]','guild') for p in peers),'Guild channel delivered')
 result['guild_literal']=True
 a.send('chat',text='/gloc')
 wait(lambda:any(e.get('source')=='server' and e.get('kind')=='system' and 'Region:200' in e.get('text','') and 'Zone:207' in e.get('text','') for e in entries(a)),'Server location message classified')
 a.send('chat',text='/loc')
 wait(lambda:any(e.get('source')=='client' and e.get('kind')=='system' and 'Connacht: loc=' in e.get('text','') for e in entries(a)),'Local location shares system channel')
 result['group_literal']=True;result['private_literal']=True;result['server_and_local_system']=True
 result['chat_entries']=[entries(p) for p in peers]
 assert before==[p.snapshot.get('inventory',{}).get('items',[]) for p in peers]
 result['inventory_unchanged']=True
 for index,p in enumerate(peers):
  (ROOT/'Reports/chat_channels'/('real_snapshot_'+str(index)+'.json')).write_text(json.dumps(p.snapshot),encoding='utf-8')
 b.send('group_leave',group_token=b.party()['token'])
 wait(lambda:all(not p.party().get('members') for p in peers),'Original group leave')
 result['leave_confirmed']=True;result['passed']=True
except Exception:result['errors'].append(traceback.format_exc())
finally:
 for index,peer in enumerate(peers):
  (RUN/('chat_trace_'+str(index)+'.json')).write_text(json.dumps(peer.trace))
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
 if server is not None and server.poll() is not None:
  with sqlite3.connect(DB) as db:db.execute('UPDATE Account SET PrivLevel=3, Realm=3 WHERE Name=?',(friend_account,))
 for handle in handles:handle.close()
 result['normal_shutdown']=all(c.returncode==0 for c,_ in clients) and server is not None and server.returncode==0
 result['passed']=result['passed'] and result['normal_shutdown'] and not result['errors']
 (ROOT/'Reports/chat_channels/real_result.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result,ensure_ascii=False),flush=True)
if not result['passed']:raise SystemExit(1)
