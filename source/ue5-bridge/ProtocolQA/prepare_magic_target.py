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
 with sqlite3.connect(DB) as db:assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name
 output=(RUN/'world_pointer_server.log').open('w',encoding='utf-8');handles.append(output)
 server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=output,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 deadline=time.monotonic()+30
 while time.monotonic()<deadline:
  try:
   with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Isolated server unavailable')
 time.sleep(2) # Listening precedes accepting logins in the original core.
 game=Path(str(INSTALL / 'new-client'));sdk=Path(str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64'))
 for character,suffix,root,port in [('Codexdruid','',RUN,19737)]:
  account='codexqa'+hashlib.sha256((RUN.name+suffix).encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name+suffix).encode()).hexdigest()[:24]
  client_env=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'],APPDATA=str(root/'appdata'))
  log=(root/'world_pointer_client.log').open('w',encoding='utf-8');handles.append(log)
  request=root/'Reports/live/logout.request'
  if request.exists():request.unlink()
  client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(game/'godot'),'--script',str(root/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character='+character],cwd=root,env=client_env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  clients.append((client,root));peers.append(Peer(port))
 wait(lambda:all(p.snapshot.get('classic_ui',{}).get('skills_ready') for p in peers),'Both actual players ready')
 a=peers[0]
 def target():return a.snapshot.get('interaction',{}).get('target',{}).get('id')
 def spawn(kind):
  previous=max([e['id'] for e in a.snapshot.get('chat',{}).get('entries',[])],default=0)
  a.send('chat',text='/mob create '+kind+' 3')
  def created():return [e for e in a.snapshot.get('chat',{}).get('entries',[]) if e['id']>previous and e['text'].startswith('Mob created: OID=')]
  wait(lambda:bool(created()),'Original creation response identifies exact new object')
  oid=int(created()[-1]['text'].split('OID=')[1]);entity='npc:'+str(oid)
  wait(lambda:any(e['id']==entity for e in a.snapshot.get('entities',[])),'Exact created NPC is available')
  return next(e for e in a.snapshot['entities'] if e['id']==entity)
 enemy=spawn('DOL.GS.GameNPC');a.send('target',entity_id=enemy['id']);settle(.2)
 for command in ['/mob name Codex Magic Target','/mob level 50','/mob realm 0','/mob aggro 0','/mob model 118']:
  a.send('chat',text=command);settle(.3)
 result['target_created']=enemy['id'];result['passed']=True

except Exception:result['errors'].append(traceback.format_exc())
finally:
 for index,peer in enumerate(peers):
  (RUN/('world_pointer_trace_'+str(index)+'.json')).write_text(json.dumps(peer.trace))
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
 for handle in handles:handle.close()
 result['normal_shutdown']=all(c.returncode==0 for c,_ in clients) and server is not None and server.returncode==0
 result['passed']=result['passed'] and result['normal_shutdown'] and not result['errors']
 (ROOT/'Reports/magic_roundtrip/target_preparation.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result,ensure_ascii=False),flush=True)
if not result['passed']:raise SystemExit(1)
