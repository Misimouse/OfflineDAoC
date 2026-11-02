from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/trainer';LIVE=R/'Reports/live';sock=None;p=None;session='';buffer=b'';snap={};serial=0
with socket.socket()as guard:guard.bind(('127.0.0.1',19727))
with(D/'trainer_capture_launcher.log').open('w',encoding='utf-8')as log:
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
  assert 'trainer' in snap['classic_ui'],'Trainer not published by current bridge'
  baseline_items=snap['inventory']['items'];baseline_points=snap['classic_ui']['points']
  # Read-only packet TrainWindow. This script never sends trainer_train, TrainSpec or TrainRealmAbility.
  sock.sendall((json.dumps(dict(type='command',session=session,id='trainer-window-real',action='trainer_refresh'))+'\n').encode());deadline=time.monotonic()+12;ready=False
  while time.monotonic()<deadline:
   try:data=sock.recv(1048576)
   except socket.timeout:continue
   if not data:break
   buffer+=data
   while b'\n' in buffer:
    line,buffer=buffer.split(b'\n',1);v=json.loads(line)
    if v.get('type')=='snapshot':snap=v
   trainer=snap.get('classic_ui',{}).get('trainer',{})
   if trainer.get('ready') and trainer.get('realm_ready') and trainer.get('preview_ready'):ready=True;break
  assert ready,'Server did not deliver original training window and preview'
  assert snap['classic_ui']['points']==baseline_points,'Read-only trainer changed points'
  assert snap['inventory']['items']==baseline_items,'Trainer query changed inventory'
  (D/'trainer_evidence.json').write_text(json.dumps({'passed':True,'real_server':True,'character':snap['classic_ui']['character'],'spec_count':len(trainer['specs']),'realm_count':len(trainer['realm']),'preview_lines':sum(len(v) for v in trainer['previews'].values()),'spec_points':trainer['spec_points'],'realm_points':trainer['realm_points'],'inventory_unchanged':True,'points_unchanged':True,'training_requests':0},indent=2),encoding='utf-8')
  snap['session']='recorded-trainer-character';(D/'real_trainer_snapshot.json').write_text(json.dumps(snap),encoding='utf-8')
  print(json.dumps({'passed':True,'specs':len(trainer['specs']),'realm':len(trainer['realm']),'preview_lines':sum(len(v) for v in trainer['previews'].values()),'real_points_spent':0}),flush=True)
 finally:
  if sock and session:sock.sendall((json.dumps(dict(type='command',session=session,id='ui-capture-logout',action='logout'))+'\n').encode())
  elif p.poll()is None:(LIVE/'logout.request').write_text('logout',encoding='utf-8')
  p.wait(timeout=100)
  if sock:sock.close()
final=json.loads((LIVE/'godot_session.json').read_text(encoding='utf-8'));report={'passed':p.returncode==0 and not final.get('playing',True),'normal_logout':not final.get('playing',True),'inventory_requests':final.get('inventory',{}).get('requests'),'bridge_rejected':final.get('bridge_rejected'),'real_server':True};(D/'real_trainer_capture.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report));assert report['passed']and report['inventory_requests']==0
