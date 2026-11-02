"""Normal GM posture round trip using the isolated candidate model catalog."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time,shutil,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/live';O=R/'Reports/pose_animations';O.mkdir(exist_ok=True)
DOTNET=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe')
def read(name):
 try:return json.loads((D/name).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
catalog_hash=hashlib.sha256((R/'models.json').read_bytes()).hexdigest()
start=time.time();samples=[]
with (O/'visual_stdout.log').open('w')as log:
 p=subprocess.Popen([DOTNET,str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--pose-test'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 while p.poll()is None and time.time()-start<240:
  path=D/'unreal_session.json'
  if path.exists()and path.stat().st_mtime>=start:samples.append({'unreal':read('unreal_session.json'),'godot':read('godot_session.json')})
  time.sleep(.15)
 if p.poll()is None:
  (D/'logout.request').write_text('logout');raise RuntimeError('Timeout; normal logout requested, process preserved')
final=read('godot_session.json');rows=[s['unreal']for s in samples];ready=[u for u in rows if u.get('player_status',{}).get('ready')]
seated=[u for u in ready if u.get('player_status',{}).get('vitals',{}).get('sitting')and u.get('local_animation')=='sit_idle']
standing=[u for u in ready if int(u.get('pose_visual_test_steps',0))==15 and not u.get('player_status',{}).get('vitals',{}).get('sitting')and u.get('local_animation')=='idle']
inventories=[{'items':u['inventory'].get('items'),'money':u['inventory'].get('money')}for u in rows if u.get('inventory',{}).get('ready')]
captures={}
for name in ['Pose_Sitting.png','Pose_Standing.png']:
 path=D/name;fresh=path.exists()and path.stat().st_mtime>=start;captures[name]=fresh
 if fresh:shutil.copy2(path,O/name)
result={'real_server':True,'character':'BridgeFighter','candidate_catalog_only':True,'normal_logout':not final.get('playing',True)and'protocolo normal'in final.get('status',''),'helper_exit_code':p.returncode,'samples':len(samples),'native_seated_pose_samples':len(seated),'native_restored_standing_samples':len(standing),'animations_observed':sorted(set(u.get('local_animation','')for u in ready)),'captures':captures,'inventory_requests':final.get('inventory',{}).get('requests'),'inventory_unchanged':bool(inventories)and all(i==inventories[0]for i in inventories),'bridge_rejected':final.get('bridge_rejected'),'move_rejected':final.get('move_rejected'),'player_state_requests':final.get('player_state_requests'),'player_state_rejected':final.get('player_state_rejected')}
result['normal_catalog_unchanged']=catalog_hash==hashlib.sha256((R/'models.json').read_bytes()).hexdigest()
result['passed']=bool(result['normal_catalog_unchanged'] and result['normal_logout']and p.returncode==0 and seated and standing and all(captures.values())and result['inventory_requests']==0 and result['inventory_unchanged']and result['bridge_rejected']==0 and result['move_rejected']==0 and result['player_state_requests']==2 and result['player_state_rejected']==0)
(O/'visual_samples.json').write_text(json.dumps(samples),encoding='utf-8');(O/'visual_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);assert result['passed']
