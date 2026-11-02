"""Read-only real GM screenshot of inventory plus merchant; no item commands."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/live';O=R/'Reports/inventory'
DOTNET=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe')
def read(name):
 try:return json.loads((D/name).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
start=time.time();samples=[]
with (O/'visual_stdout.log').open('w')as log:
 p=subprocess.Popen([DOTNET,str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--inventory-test'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 while p.poll()is None and time.time()-start<300:
  path=D/'unreal_session.json'
  if path.exists()and path.stat().st_mtime>=start:samples.append({'unreal':read('unreal_session.json'),'godot':read('godot_session.json')})
  time.sleep(.2)
 if p.poll()is None:
  (D/'logout.request').write_text('logout');raise RuntimeError('Timeout; normal logout requested, game kept alive')
final=read('godot_session.json');rows=[s['unreal']for s in samples]
ready=[u for u in rows if u.get('inventory',{}).get('ready')]
shot=D/'Ardee_GM_Client.png';capture=shot.exists()and shot.stat().st_mtime>=start
if capture:shutil.copy2(shot,O/'Inventory_GM.png')
result={'real_server':True,'character':'BridgeFighter','normal_logout':not final.get('playing',True)and'protocolo normal'in final.get('status',''),'helper_exit_code':p.returncode,'samples':len(samples),'native_inventory_ready_samples':len(ready),'max_items':max((len(u['inventory']['items']) for u in ready),default=-1),'screenshot':capture,'inventory_requests':final.get('inventory',{}).get('requests'),'inventory_rejected':final.get('inventory',{}).get('rejected'),'bridge_rejected':final.get('bridge_rejected'),'move_rejected':final.get('move_rejected')}
result['passed']=bool(result['normal_logout']and p.returncode==0 and ready and capture and result['inventory_requests']==0 and result['inventory_rejected']==0 and result['bridge_rejected']==0 and result['move_rejected']==0)
(O/'visual_samples.json').write_text(json.dumps(samples),encoding='utf-8');(O/'visual_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);assert result['passed']
