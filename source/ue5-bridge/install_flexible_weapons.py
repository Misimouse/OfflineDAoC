from pathlib import Path
import json,shutil,hashlib,datetime,os
R=Path(__file__).resolve().parent;D=R/'Reports/training_staff_fx_pets';source=R/'UnrealPlugin/DAoCVisualBridge';host=R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge';installed=R/'Client/Plugins/DAoCVisualBridge';backup=R/'Backups/FlexibleWeapons_20261102/Installed'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
proof=read(D/'flexible_complete_native.json');assert proof['passed']
reg=read(R/'Reports/ui_integration/regressions/acceptance.json');assert all(v['passed']for v in reg.values())
imp=read(D/'flexible_import.json');assert imp['passed'] and len(imp['entries'])==28
candidate=R/'equipment_catalog_flexible_candidate.json';catalog=read(candidate);flex=[v for v in catalog['models'].values()if v.get('info',{}).get('flex_file')];assert len(flex)==39 and all(v['type']=='skeletal' and v.get('complete_bone_tracks') for v in flex)
files=[]
for p in (source/'Source').rglob('*'):
 if p.is_file():
  rel=p.relative_to(source);assert sha(p)==sha(host/rel);files.append((p,rel))
for n in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor-DAoCVisualBridge.pdb','UnrealEditor.modules']:
 rel=Path('Binaries/Win64')/n;files.append((host/rel,rel))
for p in (source/'Content/FlexibleWeapons_v02').rglob('*'):
 if p.is_file():
  rel=p.relative_to(source);assert sha(p)==sha(host/rel);files.append((p,rel))
for p,rel in files:
 dest=installed/rel
 if dest.exists():
  b=backup/rel;b.parent.mkdir(parents=True,exist_ok=True)
  if not b.exists():shutil.copy2(dest,b)
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(p)==sha(dest)
old=backup/'equipment_catalog_v01.json';old.parent.mkdir(parents=True,exist_ok=True)
if not old.exists():shutil.copy2(R/'equipment_catalog_v01.json',old)
tmp=R/'equipment_catalog_v01.pending.json';shutil.copy2(candidate,tmp);os.replace(tmp,R/'equipment_catalog_v01.json');assert sha(candidate)==sha(R/'equipment_catalog_v01.json')
poses=read(R/'Reports/equipment/fixture.json.flexible-poses.json')['models'] if (R/'Reports/equipment/fixture.json.flexible-poses.json').exists() else []
# General regression does not overwrite the dedicated flexible-pose artifact.
manifest={'installed':True,'at':datetime.datetime.now().isoformat(),'models':39,'unique_geometry_grips':28,'clips_per_model':9,'native_flexible_checks':proof['checks'],'general_native_checks':sum(v['checks']for v in reg.values()),'idle_pose_max_error_cm':max(v['max_error_cm']for v in poses),'attack_pose_max_error_cm':max(v['attack_error_cm']for v in poses),'render_bounds_verified':all(v['bounds_contain_poses']for v in poses),'original_action_clock':True,'game_language':'English','work_modified':False,'server_modified':False,'catalog_sha256':sha(candidate),'files_sha256':{str(rel):sha(p)for p,rel in files},'previous_manifest':'Reports/training_staff_fx_pets/installation.json','performance_limit':'GPU 96-98 percent with two WORK editors and private client closed; isolated FPS benchmark pending. Their projects were not altered.','remaining_visual_parity':['Weapon dyes, guild emblems and permanent weapon effects remain pending.']}
(D/'flexible_installation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in manifest.items()if k!='files_sha256'}),flush=True)
