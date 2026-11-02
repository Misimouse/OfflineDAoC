"""Request normal local server shutdown through the existing administrator character."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/gm_mode';buffer=b'';session='';snapshot={};serial=0;sock=None;proc=None
report={'shutdown_requested_via_normal_command':False,'server_stopped':False,'errors':[]}
def pump(seconds=.15):
 global buffer,session,snapshot
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  try:data=sock.recv(1048576)
  except socket.timeout:continue
  if not data:return False
  buffer+=data
  while b'\n' in buffer:
   raw,buffer=buffer.split(b'\n',1);v=json.loads(raw)
   if v.get('type')=='hello':session=v['session']
   if v.get('type')=='snapshot':snapshot=v
 return True
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='gm-maintenance:'+str(serial),action=action,**values))+'\n').encode())
def listening(port):
 with socket.socket() as s:s.settimeout(.3);return s.connect_ex(('127.0.0.1',port))==0
try:
 assert listening(10300) and not listening(19727),'Maintenance requires server running without a game session'
 log=(D/'maintenance_launcher.log').open('w')
 proc=subprocess.Popen([str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--session-only'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 deadline=time.monotonic()+85
 while time.monotonic()<deadline:
  try:sock=socket.create_connection(('127.0.0.1',19727),timeout=.2);break
  except OSError:time.sleep(.2)
 assert sock is not None,'No bridge maintenance session';sock.settimeout(.15)
 deadline=time.monotonic()+85
 while time.monotonic()<deadline:
  pump()
  if session and snapshot.get('in_game') and snapshot.get('player_status',{}).get('ready'):break
 assert session and snapshot.get('in_game'),'No normal login'
 send('chat',text='/shutdown 10');report['shutdown_requested_via_normal_command']=True;print('Normal administrator shutdown requested; waiting for server save',flush=True);pump(1)
 report['messages']=snapshot.get('interaction',{}).get('messages',[])[-8:]
 send('logout')
 deadline=time.monotonic()+55
 while time.monotonic()<deadline and listening(10300):
  pump(.3)
 report['server_stopped']=not listening(10300);assert report['server_stopped'],'Normal shutdown did not stop server; no force close attempted'
 if proc is not None:
  try:proc.wait(timeout=100)
  except subprocess.TimeoutExpired:report['errors'].append('Maintenance session still awaiting normal exit; process not killed')
except Exception:report['errors'].append(traceback.format_exc())
finally:
 if sock is not None:
  try:
   if session and listening(19727):send('logout')
  except OSError:pass
  sock.close()
 (D/'maintenance_shutdown.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
 if report['errors'] or not report['server_stopped']:raise SystemExit(1)
