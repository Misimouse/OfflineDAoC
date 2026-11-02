"""Local server owner retaining stdin so updates can request a normal exit/save."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import subprocess,time,json,os,socket
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/gm_mode';I=Path(str(INSTALL));request=D/'server_stop.request';state=D/'server_host.json'
def listening():
 with socket.socket() as s:s.settimeout(.3);return s.connect_ex(('127.0.0.1',10300))==0
if listening():raise SystemExit('Existing server preserved; host did not start another')
if request.exists():request.unlink()
env=dict(os.environ,DOTNET_ROOT=str(I/'tools/dotnet'),DOTNET_ROOT_X64=str(I/'tools/dotnet'))
with (D/'server_host_console.log').open('a',encoding='utf-8') as log:
 p=subprocess.Popen([str(I/'tools/dotnet/dotnet.exe'),str(I/'runtime/server/CoreServer.dll'),'--start'],cwd=I/'runtime/server',env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 state.write_text(json.dumps({'running':True,'server_pid':p.pid,'controller_pid':os.getpid(),'stop_request':str(request)},indent=2))
 try:
  while p.poll() is None:
   if request.exists():
    request.unlink();p.stdin.write('exit\n');p.stdin.flush()
    state.write_text(json.dumps({'running':True,'server_pid':p.pid,'normal_shutdown_requested':True},indent=2));p.wait(timeout=120);break
   time.sleep(.5)
 finally:
  if p.poll() is None:
   try:p.stdin.write('exit\n');p.stdin.flush();p.wait(timeout=120)
   except (OSError,subprocess.TimeoutExpired):pass
  state.write_text(json.dumps({'running':p.poll() is None,'server_pid':p.pid,'exit_code':p.poll()},indent=2))
