"""Read-only merchant/target probe with the real GM; no purchases or quest replies."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/live';O=R/'Reports/interactions'
DOTNET=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe')
def read(name):
 try:return json.loads((D/name).read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
start=time.time();samples=[]
with (O/'live_stdout.log').open('w')as log:
 p=subprocess.Popen([DOTNET,str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--interaction-test'],cwd=R,stdout=log,stderr=subprocess.STDOUT)
 while p.poll()is None and time.time()-start<300:
  path=D/'unreal_session.json'
  if path.exists()and path.stat().st_mtime>=start:
   samples.append({'unreal':read('unreal_session.json'),'godot':read('godot_session.json')})
  time.sleep(.2)
 if p.poll()is None:
  (D/'logout.request').write_text('logout');raise RuntimeError('Timeout; normal logout requested. No game process killed.')
final=read('godot_session.json');rows=[s['unreal']for s in samples]
merchants=[u.get('interaction',{}).get('merchant',{})for u in rows]
items=max((sum(len(v)for v in m.get('pages',{}).values())for m in merchants),default=0)
targets=[u.get('interaction',{}).get('target',{})for u in rows]
steps=max((u.get('interaction_test_steps',0)for u in rows),default=0)
shot=D/'Ardee_GM_Client.png';capture=shot.exists()and shot.stat().st_mtime>=start
if capture:shutil.copy2(shot,O/'Merchant_GM.png')
result={'real_server':True,'character':'BridgeFighter','normal_logout':not final.get('playing',True)and'protocolo normal'in final.get('status',''),'helper_exit_code':p.returncode,'samples':len(samples),'max_merchant_items':items,'target_ids':sorted(set(t.get('id','')for t in targets)-{''}),'native_test_bits':steps,'screen_picking_passed':bool(steps&4),'interaction_requests':final.get('interaction_requests',0),'interaction_responses':final.get('interaction_responses',0),'interaction_rejected':final.get('interaction_rejected',0),'bridge_rejected':final.get('bridge_rejected',0),'move_rejected':final.get('move_rejected',0),'screenshot':capture}
result['passed']=bool(result['normal_logout']and p.returncode==0 and items>0 and steps&1 and steps&2 and steps&4 and result['interaction_responses']>0 and result['interaction_rejected']==0 and result['bridge_rejected']==0 and result['move_rejected']==0 and capture)
(O/'live_samples.json').write_text(json.dumps(samples),encoding='utf-8');(O/'live_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
assert result['passed'],'Real interaction test failed; inspect sanitized reports.'
