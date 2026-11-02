from pathlib import Path
import shutil,json,hashlib,datetime
R=Path(__file__).resolve().parent
D=R/'Reports/training_staff_fx_pets';source=R/'UnrealPlugin/DAoCVisualBridge';host=R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge';installed=R/'Client/Plugins/DAoCVisualBridge';backup=R/'Backups/TrainingStaffFxPets_20261102/Installed'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
reg=read(R/'Reports/ui_integration/regressions/acceptance.json');assert all(v['passed']for v in reg.values())
body=read(R/'Reports/equipment/fixture.json.native.json');assert body['passed']
fx=read(D/'fx_native.json');assert fx['passed']
pet=read(D/'pet_real.json');assert pet['passed']
dummy=read(D/'dummy_server_result.json');assert dummy['passed']
assert read(D/'visual/visual_render.json')['passed']
assert read(R/'Reports/equipment/all_import.json')['complete'] and not read(R/'Reports/equipment/all_import.json')['errors']
files=[]
for p in (source/'Source').rglob('*'):
 if p.is_file():
  rel=p.relative_to(source);assert sha(p)==sha(host/rel);files.append((p,rel))
rel=Path('DAoCVisualBridge.uplugin');assert sha(source/rel)==sha(host/rel);files.append((source/rel,rel))
for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor-DAoCVisualBridge.pdb','UnrealEditor.modules']:
 rel=Path('Binaries/Win64')/name;files.append((host/rel,rel))
for folder in ['Equipment_v02','Equipment_All_v01','SpellVisuals_v01','TrainingDummy_v01','PetModels_v01','ClassicUI']:
 for p in (source/'Content'/folder).rglob('*'):
  if p.is_file():
   rel=p.relative_to(source);assert sha(p)==sha(host/rel),(rel,'candidate content mismatch');files.append((p,rel))
for p,rel in files:
 dest=installed/rel
 if dest.exists():
  old=backup/rel;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,old)
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(dest)==sha(p)
manifest={'installed':True,'at':datetime.datetime.now().isoformat(),'native_checks':sum(v['checks']for v in reg.values())-reg['equipment']['checks']+body['checks'],'fx_checks':fx['checks'],'viewport_checks':read(R/'Reports/viewport_map/fixture.json.native.json')['checks'],'chat_checks':read(R/'Reports/chat_channels/fixture.json.native.json')['checks'],'real_pet_commands_verified':True,'original_training_dummy':dummy,'weapon_model_count':len(read(R/'equipment_catalog_v01.json')['models']),'game_language':'English','work_modified':False,'previous_manifest':'Reports/magic_roundtrip/installation.json','files_sha256':{str(rel):sha(p)for p,rel in files},'catalogs_sha256':{name:sha(R/name)for name in ['models.json','models_animations_v02.json','equipment_catalog_v01.json']},'remaining_limits':['Flexible weapons currently retain original bind pose; own chain animation pending.','Rare spell UV/controller combinations still need per-effect visual review.','Server navmesh remains original; remastered obstacle divergence is stopped by the native collision layer.']}
(D/'installation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in manifest.items()if k not in ['files_sha256','catalogs_sha256','original_training_dummy']}),flush=True)
