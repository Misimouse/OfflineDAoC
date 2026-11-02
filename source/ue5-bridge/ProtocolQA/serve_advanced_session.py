import sys as _bridge_sys
from pathlib import Path as _BridgePath
_bridge_sys.path.insert(0,str(_BridgePath(__file__).resolve().parents[1]))
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from qa_runtime import *
import subprocess,socket,time,hashlib,sqlite3
assert DB.is_relative_to(RUN)
with sqlite3.connect(DB) as db:
 assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name
 assert db.execute("SELECT Class,Level FROM DOLCharacters WHERE Name='Codexdruid'").fetchone()==(47,50)
account='codexqa'+hashlib.sha256(RUN.name.encode()).hexdigest()[:10]
password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name).encode()).hexdigest()[:24]
server=None;client=None
with (RUN/'advanced_server.log').open('w',encoding='utf-8') as output:
 try:
  server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=output,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
  deadline=time.monotonic()+35
  while time.monotonic()<deadline and server.poll() is None:
   try:
    with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
   except OSError:time.sleep(.2)
  else:raise RuntimeError('Isolated server unavailable')
  game=Path(str(INSTALL / 'new-client'))
  sdk=Path(str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64'))
  client_env=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'])
  with (RUN/'advanced_client.log').open('w',encoding='utf-8') as client_log:
   client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(game/'godot'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character=Codexdruid'],env=client_env,cwd=RUN,stdout=client_log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   print('Disposable advanced session started on bridge 19737.',flush=True)
   deadline=time.monotonic()+480
   while client.poll() is None and time.monotonic()<deadline and not (RUN/'finish.request').exists():time.sleep(.3)
   if client.poll() is None:
    (RUN/'Reports/live/logout.request').write_text('logout')
    client.wait(timeout=100)
   print(json.dumps({'client_exit':client.returncode,'disposable_session':True}),flush=True)
 finally:
  if client is not None and client.poll() is None:client.kill();client.wait(timeout=10)
  if server is not None and server.poll() is None:
   server.stdin.write('exit\n');server.stdin.flush()
   try:server.wait(timeout=40)
   except subprocess.TimeoutExpired:server.kill();server.wait(timeout=10)
