"""Verify coherent installed targets and the bounded scope of real-server checks."""
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/player_state'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
log=(D/'build_full.log').read_text(errors='replace');targets=['UnrealEditor Win64 Development','UnrealGame Win64 Development','UnrealGame Win64 Shipping']
assert 'BUILD SUCCESSFUL'in log and all(t in log for t in targets)
files=[]
for folder in ['Binaries','Source']:
 src=R/'Build/DAoCVisualBridge'/folder
 for p in src.rglob('*'):
  if not p.is_file():continue
  relative=p.relative_to(src);q=R/'Client/Plugins/DAoCVisualBridge'/folder/relative;digest=hashlib.sha256(p.read_bytes()).hexdigest()
  assert q.is_file()and hashlib.sha256(q.read_bytes()).hexdigest()==digest,str(q)
  if folder=='Source':assert (R/'UnrealPlugin/DAoCVisualBridge/Source'/relative).read_bytes()==p.read_bytes(),str(relative)
  files.append({'path':folder+'/'+relative.as_posix(),'sha256':digest})
checks={}
for name in ['godot_tests.json','combat_entity_tests.json','server_verification.json','server_verification.json.native.json','visual_verification.json']:
 data=read(D/name);assert data['passed'],name;checks[name]={'passed':True,'checks':data.get('checks')}
live=read(D/'server_verification.json');assert live['normal_logout']and live['inventory_unchanged']and live['final_inventory_unchanged']and live['bridge_rejected']==0 and live['player_state_rejected']==0
ui=read(D/'visual_verification.json');keyboard=read(D/'keyboard_verification.json');assert keyboard['passed']and keyboard['bridge_rejected']==0 and keyboard['inventory_requests']==0
result={'complete':True,'targets':targets,'files':files,'checks':checks,'real_status_posture_weapon_mode_verified':True,'native_hud_keyboard_verified':True,'real_enemy_combat_verified':False,'combat_animations_active':False,'full_client_parity':False,'original_inventory_unchanged':True,'normal_logout':True}
(D/'installed_build.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in ['files','checks']}))
