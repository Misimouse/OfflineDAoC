import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/pose_animations'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
log=(D/'build_full.log').read_text(errors='replace');targets=['UnrealEditor Win64 Development','UnrealGame Win64 Development','UnrealGame Win64 Shipping'];assert 'BUILD SUCCESSFUL'in log and all(t in log for t in targets)
files=[]
for folder in ['Binaries','Source','Content']:
 source=R/'Build/DAoCVisualBridge'/folder
 for path in source.rglob('*'):
  if not path.is_file():continue
  relative=path.relative_to(source);installed=R/'Client/Plugins/DAoCVisualBridge'/folder/relative;digest=hashlib.sha256(path.read_bytes()).hexdigest()
  assert installed.is_file()and hashlib.sha256(installed.read_bytes()).hexdigest()==digest,str(installed)
  if folder=='Source':assert(R/'UnrealPlugin/DAoCVisualBridge/Source'/relative).read_bytes()==path.read_bytes()
  files.append({'path':folder+'/'+relative.as_posix(),'sha256':digest})
proof=read(D/'export_verification.json');assets=read(D/'asset_validation.json');native=read(D/'native_tests.json');live=read(D/'visual_verification.json');promotion=read(D/'catalog_promotion.json');motion=read(R/'Reports/movement/server_trace.json.motion-results.json')
assert proof['passed']and assets['passed']and native['passed']and native['checks']>=26 and live['passed']and promotion['active']and motion['passed']
active=read(R/'models.json');candidate=read(R/'models_animations_v02.json');assert active==candidate
assert live['normal_logout']and live['inventory_unchanged']and live['bridge_rejected']==0 and live['move_rejected']==0
result={'complete':True,'targets':targets,'files':files,'base_models':len(assets['models']),'original_clips':sum(len(m['validated_clips'])for m in assets['models'].values()),'geometry_skin_transforms_unchanged':True,'original_materials_preserved':True,'native_pose_checks':native['checks'],'movement_checks':motion['checks'],'catalog_active':True,'real_sit_stand_verified':True,'inventory_unchanged':True,'normal_logout':True,'real_death_verified':False,'attacks_spells_styles_implemented':False,'full_client_parity':False}
(D/'installed_build.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='files'}))
