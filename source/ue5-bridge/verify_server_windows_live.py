from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/server_windows';LIVE=R/'Reports/live';sock=None;p=None;session='';buffer=b'';snap={};serial=0
with socket.socket()as guard:guard.bind(('127.0.0.1',19727))
with(D/'server_window_capture_launcher.log').open('w',encoding='utf-8')as log:
 p=subprocess.Popen([str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--session-only'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 try:
  deadline=time.monotonic()+85
  while time.monotonic()<deadline:
   try:sock=socket.create_connection(('127.0.0.1',19727),timeout=.2);break
   except OSError:time.sleep(.2)
  assert sock;sock.settimeout(.2);deadline=time.monotonic()+35;ready_at=None
  while time.monotonic()<deadline:
   try:data=sock.recv(1048576)
   except socket.timeout:continue
   if not data:break
   buffer+=data
   while b'\n'in buffer:
    line,buffer=buffer.split(b'\n',1);v=json.loads(line)
    if v.get('type')=='hello':session=v['session']
    if v.get('type')=='snapshot':snap=v
   ui=snap.get('classic_ui',{})
   if ui.get('ready') and ui.get('skills_ready') and snap.get('inventory',{}).get('ready'):
    if ready_at is None:ready_at=time.monotonic()
    if time.monotonic()-ready_at>3:break
  assert snap.get('classic_ui',{}).get('ready') and snap['classic_ui']['skills_ready'],'Actual character UI lists not ready'
  assert 'server_window' in snap['classic_ui'],'Server information not published by current bridge'
  baseline_items=snap['inventory']['items'];baseline_points=snap['classic_ui']['points'];baseline_quests=snap['classic_ui']['journal']['entries']
  sock.sendall((json.dumps(dict(type='command',session=session,id='realm-window-real',action='chat',text='/realm'))+'\n').encode());deadline=time.monotonic()+10;ready=False
  previous=snap['classic_ui']['server_window'].get('token','')
  while time.monotonic()<deadline:
   try:data=sock.recv(1048576)
   except socket.timeout:continue
   if not data:break
   buffer+=data
   while b'\n' in buffer:
    line,buffer=buffer.split(b'\n',1);v=json.loads(line)
    if v.get('type')=='snapshot':snap=v
   window=snap.get('classic_ui',{}).get('server_window',{})
   if window.get('status')=='ready' and window.get('token')!=previous:ready=True;break
  assert ready,'Realm information did not reach the bridge reader'
  assert snap['classic_ui']['points']==baseline_points and snap['classic_ui']['journal']['entries']==baseline_quests,'Read-only information changed progress'
  assert snap['inventory']['items']==baseline_items,'Information query changed inventory'
  (D/'server_window_evidence.json').write_text(json.dumps({'passed':True,'real_server':True,'character':snap['classic_ui']['character'],'caption':window['caption'],'lines':len(window['lines']),'inventory_unchanged':True,'points_unchanged':True,'quests_unchanged':True,'gameplay_mutations':0},indent=2),encoding='utf-8')
  snap['session']='recorded-server-window';(D/'real_server_window_snapshot.json').write_text(json.dumps(snap),encoding='utf-8')
  sock.sendall((json.dumps(dict(type='command',session=session,id='realm-window-close',action='ui_server_window_close',window_token=window['token']))+'\n').encode());deadline=time.monotonic()+5;closed=False
  while time.monotonic()<deadline:
   try:data=sock.recv(1048576)
   except socket.timeout:continue
   if not data:break
   buffer+=data
   while b'\n' in buffer:
    line,buffer=buffer.split(b'\n',1);v=json.loads(line)
    if v.get('type')=='snapshot':snap=v
   if not snap.get('classic_ui',{}).get('server_window',{}):closed=True;break
  assert closed,'Read-only server window did not close'
  print(json.dumps({'passed':True,'caption':window['caption'],'lines':len(window['lines']),'closed':closed,'gameplay_mutations':0}),flush=True)
 finally:
  if sock and session:sock.sendall((json.dumps(dict(type='command',session=session,id='ui-capture-logout',action='logout'))+'\n').encode())
  elif p.poll()is None:(LIVE/'logout.request').write_text('logout',encoding='utf-8')
  p.wait(timeout=100)
  if sock:sock.close()
final=json.loads((LIVE/'godot_session.json').read_text(encoding='utf-8'));report={'passed':p.returncode==0 and not final.get('playing',True),'normal_logout':not final.get('playing',True),'inventory_requests':final.get('inventory',{}).get('requests'),'bridge_rejected':final.get('bridge_rejected'),'real_server':True};(D/'real_server_window_capture.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report));assert report['passed']and report['inventory_requests']==0
