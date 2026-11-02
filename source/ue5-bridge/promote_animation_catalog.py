"""Activate only the model/animation paths validated against the existing look."""
import json,hashlib,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/pose_animations'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
proof=read(D/'export_verification.json');assets=read(D/'asset_validation.json');native=read(D/'native_tests.json');live=read(D/'visual_verification.json')
assert proof['passed']and len(proof['models'])==22 and assets['passed']and len(assets['models'])==22 and native['passed']and native['checks']>=26 and live['passed']and live['normal_catalog_unchanged']and live['normal_logout']
before=R/'models.json';candidate=R/'models_animations_v02.json';old=read(before);new=read(candidate);assert set(old)==set(new)
for ident in old:
 for key in ['type','scale','yaw_offset','name','shared_base']:
  assert old[ident].get(key)==new[ident].get(key),(ident,key)
backup=R/'Backups/pre-animations-catalog-20261101/models.json';backup.parent.mkdir(exist_ok=True)
if not backup.exists():shutil.copy2(before,backup)
old_hash=hashlib.sha256(before.read_bytes()).hexdigest();shutil.copy2(candidate,before)
result={'active':True,'base_models':22,'catalog_entries':len(new),'geometry_skin_transforms_unchanged':True,'original_materials_preserved':True,'appearance_fields_unchanged':True,'before_sha256':old_hash,'active_sha256':hashlib.sha256(before.read_bytes()).hexdigest(),'backup':str(backup),'real_posture_verified':True,'real_death_verified':False,'combat_abilities_complete':False}
(D/'catalog_promotion.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
