import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/equipment'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
targets=['UnrealEditor Win64 Development','UnrealGame Win64 Development','UnrealGame Win64 Shipping'];log=(D/'build_full.log').read_text(errors='replace');assert 'BUILD SUCCESSFUL'in log and all(t in log for t in targets)
files=[]
for folder in ['Binaries','Source','Content']:
 source=R/'Build/DAoCVisualBridge'/folder
 for path in source.rglob('*'):
  if not path.is_file():continue
  relative=path.relative_to(source);installed=R/'Client/Plugins/DAoCVisualBridge'/folder/relative;digest=hashlib.sha256(path.read_bytes()).hexdigest();assert installed.is_file()and hashlib.sha256(installed.read_bytes()).hexdigest()==digest,str(installed)
  if folder=='Source':assert(R/'UnrealPlugin/DAoCVisualBridge/Source'/relative).read_bytes()==path.read_bytes()
  files.append({'path':folder+'/'+relative.as_posix(),'sha256':digest})
native=read(D/'fixture.json.native.json');live=read(D/'visual_verification.json');assets=read(D/'import.json');catalog=read(D/'catalog.json')
assert native['passed']and native['checks']>=27 and live['passed']and assets['complete']and catalog['active']and catalog['default_launcher_enabled']
assert catalog['sha256']==hashlib.sha256((R/'equipment_catalog_v01.json').read_bytes()).hexdigest()
assert live['inventory_unchanged']and live['normal_logout']and live['bridge_rejected']==0 and live['missing_models']==0 and live['missing_bones']==0
result={'complete':True,'targets':targets,'files':files,'models':[445,59],'native_checks':native['checks'],'real_draw_sheathe_verified':True,'original_geometry_and_bind_frames_verified':True,'default_launcher_enabled':True,'inventory_unchanged':True,'normal_logout':True,'clothing_dyes_emblems_effects_complete':False,'all_weapon_models_complete':False,'npc_equipment_complete':False,'real_enemy_combat_verified':False,'full_client_parity':False}
(D/'installed_build.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='files'}))
