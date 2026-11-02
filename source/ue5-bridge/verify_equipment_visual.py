"""Real GM draw/sheath round trip; no target, item operations or resource grants."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/live';O=R/'Reports/equipment';O.mkdir(exist_ok=True)
DOTNET=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe')
def read(name):
 try:return json.loads((D/name).read_text(encoding='utf-8-sig'))
 except(OSError,ValueError):return {}
def bindings(row):return {int(b['slot']):b for b in row.get('equipment_visual',{}).get('bindings',[])}
def has_pair(row,sword_bone):
 b=bindings(row);return len(b)==2 and b.get(10,{}).get('model')==445 and b[10].get('bone')==sword_bone and b.get(11,{}).get('model')==59 and b[11].get('bone')=='Bip01-L-Shield'and all(v.get('component_valid')for v in b.values())
start=time.time();samples=[]
with(O/'visual_stdout.log').open('w')as log:
 p=subprocess.Popen([DOTNET,str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--equipment-test'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 while p.poll()is None and time.time()-start<250:
  path=D/'unreal_session.json'
  if path.exists()and path.stat().st_mtime>=start:samples.append({'unreal':read('unreal_session.json'),'godot':read('godot_session.json')})
  time.sleep(.15)
 if p.poll()is None:
  (D/'logout.request').write_text('logout');raise RuntimeError('Timeout; normal logout requested, process preserved')
final=read('godot_session.json');rows=[s['unreal']for s in samples];ready=[u for u in rows if u.get('inventory',{}).get('ready')and u.get('player_status',{}).get('ready')]
sheathed=[u for u in ready if not u['player_status'].get('attack_on')and has_pair(u,'Bip01-L-Belt')]
drawn=[u for u in ready if u['player_status'].get('attack_on')and has_pair(u,'Bip01-R-Held')]
restored=[u for u in sheathed if u.get('equipment_visual',{}).get('visual_test_steps')==31]
inventories=[{'items':u['inventory'].get('items'),'money':u['inventory'].get('money')}for u in ready]
captures={}
for name in ['Equipment_Sheathed.png','Equipment_Drawn.png','Equipment_Restored.png']:
 path=D/name;fresh=path.exists()and path.stat().st_mtime>=start;captures[name]=fresh
 if fresh:shutil.copy2(path,O/name)
result={'real_server':True,'character':'BridgeFighter','normal_logout':not final.get('playing',True)and'protocolo normal'in final.get('status',''),'helper_exit_code':p.returncode,'samples':len(samples),'sheathed_samples':len(sheathed),'drawn_samples':len(drawn),'restored_samples':len(restored),'captures':captures,'inventory_unchanged':bool(inventories)and all(i==inventories[0]for i in inventories),'inventory_requests':final.get('inventory',{}).get('requests'),'player_state_requests':final.get('player_state_requests'),'player_state_rejected':final.get('player_state_rejected'),'bridge_rejected':final.get('bridge_rejected'),'move_rejected':final.get('move_rejected'),'missing_models':max((u.get('equipment_visual',{}).get('missing_models',0)for u in ready),default=-1),'missing_bones':max((u.get('equipment_visual',{}).get('missing_bones',0)for u in ready),default=-1)}
result['passed']=bool(result['normal_logout']and p.returncode==0 and sheathed and drawn and restored and all(captures.values())and result['inventory_unchanged']and result['inventory_requests']==0 and result['player_state_requests']==2 and result['player_state_rejected']==0 and result['bridge_rejected']==0 and result['move_rejected']==0 and result['missing_models']==0 and result['missing_bones']==0)
(O/'visual_samples.json').write_text(json.dumps(samples));(O/'visual_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);assert result['passed']
