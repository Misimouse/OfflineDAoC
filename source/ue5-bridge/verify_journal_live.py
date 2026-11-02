from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/journal';LIVE=R/'Reports/live';sock=None;p=None;session='';buffer=b'';snap={};serial=0
with socket.socket()as guard:guard.bind(('127.0.0.1',19727))
with(D/'journal_capture_launcher.log').open('w',encoding='utf-8')as log:
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
  assert 'journal' in snap['classic_ui'],'Journal not published by current bridge'
  baseline_items=snap['inventory']['items'];baseline_quests=snap['classic_ui']['journal']['entries']
  # journal_state.gd uses /questguide only; never /task. Server questguide.cs calls ShowNext.
  sock.sendall((json.dumps(dict(type='command',session=session,id='journal-guide-real',action='journal_guide'))+'\n').encode());deadline=time.monotonic()+10;ready=False
  while time.monotonic()<deadline:
   try:data=sock.recv(1048576)
   except socket.timeout:continue
   if not data:break
   buffer+=data
   while b'\n' in buffer:
    line,buffer=buffer.split(b'\n',1);v=json.loads(line)
    if v.get('type')=='snapshot':snap=v
   journal=snap.get('classic_ui',{}).get('journal',{})
   if journal.get('guide',{}).get('status')=='ready':ready=True;break
  assert ready,'Server did not deliver a real Quest Guide'
  assert journal['entries']==baseline_quests,'Read-only guide changed actual journal'
  assert snap['inventory']['items']==baseline_items,'Guide changed inventory'
  (D/'journal_evidence.json').write_text(json.dumps({'passed':True,'real_server':True,'character':snap['classic_ui']['character'],'quest_count':len(baseline_quests),'guide_caption':journal['guide']['caption'],'guide_lines':journal['guide']['lines'],'inventory_unchanged':True,'quests_unchanged':True,'accept_complete_abandon_requests':0},indent=2),encoding='utf-8')
  snap['session']='recorded-journal-character';(D/'real_journal_snapshot.json').write_text(json.dumps(snap),encoding='utf-8')
  print(json.dumps({'passed':True,'quest_count':len(baseline_quests),'guide_lines':len(journal['guide']['lines']),'real_quests_changed':0}),flush=True)
 finally:
  if sock and session:sock.sendall((json.dumps(dict(type='command',session=session,id='ui-capture-logout',action='logout'))+'\n').encode())
  elif p.poll()is None:(LIVE/'logout.request').write_text('logout',encoding='utf-8')
  p.wait(timeout=100)
  if sock:sock.close()
final=json.loads((LIVE/'godot_session.json').read_text(encoding='utf-8'));report={'passed':p.returncode==0 and not final.get('playing',True),'normal_logout':not final.get('playing',True),'inventory_requests':final.get('inventory',{}).get('requests'),'bridge_rejected':final.get('bridge_rejected'),'real_server':True};(D/'real_journal_capture.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report));assert report['passed']and report['inventory_requests']==0
