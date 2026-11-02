import sys as _bridge_sys
from pathlib import Path as _BridgePath
_bridge_sys.path.insert(0,str(_BridgePath(__file__).resolve().parents[1]))
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from qa_runtime import *
import subprocess,socket,time,hashlib,sqlite3
assert DB.is_relative_to(RUN)
with sqlite3.connect(DB) as guard:assert guard.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name
with sqlite3.connect(DB) as db:
 assert db.execute('SELECT count(*) FROM Account').fetchone()[0]==1
 assert db.execute('SELECT count(*) FROM DOLCharacters').fetchone()[0]==1
account='codexqa'+hashlib.sha256((RUN.name+':friend').encode()).hexdigest()[:10]
password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name+':friend').encode()).hexdigest()[:24]
server=None;client=None
with (RUN/'create_server.log').open('w',encoding='utf-8') as output:
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
  with (RUN/'create_client.log').open('w',encoding='utf-8') as client_log:
   client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(game/'godot'),'--script',str(RUN/'Godot/create_qa_friend.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world'],env=client_env,cwd=RUN,stdout=client_log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   client.wait(timeout=65)
  result=json.loads((RUN/'creation_result.json').read_text())
  assert client.returncode==0 and result['passed'],result
  print(json.dumps(result),flush=True)
 finally:
  if client is not None and client.poll() is None:client.kill();client.wait(timeout=10)
  if server is not None and server.poll() is None:
   server.stdin.write('exit\n');server.stdin.flush()
   try:server.wait(timeout=40)
   except subprocess.TimeoutExpired:server.kill();server.wait(timeout=10)
