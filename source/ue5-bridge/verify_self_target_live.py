from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/group';LIVE=R/'Reports/live';sock=None;p=None;session='';buffer=b'';snap={};serial=0
with socket.socket()as guard:guard.bind(('127.0.0.1',19727))
with(D/'self_capture_launcher.log').open('w',encoding='utf-8')as log:
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
  baseline_items=snap['inventory']['items']
  sock.sendall((json.dumps(dict(type='command',session=session,id='self-target-real',action='target_self'))+'\n').encode());deadline=time.monotonic()+8;targeted=False
  while time.monotonic()<deadline:
   try:data=sock.recv(1048576)
   except socket.timeout:continue
   if not data:break
   buffer+=data
   while b'\n' in buffer:
    line,buffer=buffer.split(b'\n',1);v=json.loads(line)
    if v.get('type')=='snapshot':snap=v
   t=snap.get('interaction',{}).get('target',{})
   if t.get('id')=='player:local' and t.get('name')==snap['classic_ui']['character'] and abs(t.get('health',-1)-snap['player_status']['vitals']['health_pct']/100)<.001:
    targeted=True;break
  assert targeted,'Own target name and actual health must be present'
  assert snap['inventory']['items']==baseline_items,'Self target changed inventory'
  (D/'self_target_evidence.json').write_text(json.dumps({'passed':True,'real_server':True,'name':t['name'],'target_id':t['id'],'health':t['health'],'inventory_unchanged':True,'group_mutations':0,'human_invites_sent':0},indent=2),encoding='utf-8')
  snap['session']='recorded-ui-character';(D/'real_self_snapshot.json').write_text(json.dumps(snap),encoding='utf-8')
  print(json.dumps({'character':snap['classic_ui']['character'],'entries':len(snap['classic_ui']['entries']),'specs':len(snap['classic_ui']['specs']),'stats':snap['classic_ui']['stats'],'class':snap['classic_ui']['info'].get('class_name'),'bars':len(snap['classic_ui']['bars']),'item_operations':0}),flush=True)
 finally:
  if sock and session:sock.sendall((json.dumps(dict(type='command',session=session,id='ui-capture-logout',action='logout'))+'\n').encode())
  elif p.poll()is None:(LIVE/'logout.request').write_text('logout',encoding='utf-8')
  p.wait(timeout=100)
  if sock:sock.close()
final=json.loads((LIVE/'godot_session.json').read_text(encoding='utf-8'));report={'passed':p.returncode==0 and not final.get('playing',True),'normal_logout':not final.get('playing',True),'inventory_requests':final.get('inventory',{}).get('requests'),'bridge_rejected':final.get('bridge_rejected'),'real_server':True};(D/'real_self_capture.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report));assert report['passed']and report['inventory_requests']==0
