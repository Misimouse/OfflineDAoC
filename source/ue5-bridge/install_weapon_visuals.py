from pathlib import Path
import json,shutil,hashlib,os,datetime
R=Path(__file__).resolve().parent;D=R/'Reports/training_staff_fx_pets'
source=R/'UnrealPlugin/DAoCVisualBridge';host=R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge';installed=R/'Client/Plugins/DAoCVisualBridge'
backup=R/'Backups/PermanentWeaponEffects_20261102/Installed'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
proof=read(D/'weapon_fx_native.json');frames=read(D/'weapon_fx_frames.json');export=read(D/'weapon_fx_export.json');imp=read(D/'fx_import.json')
assert proof['passed'] and frames['passed'] and export['passed'] and imp['passed']
candidate=R/'equipment_catalog_weapon_fx_candidate.json';catalog=read(candidate)
assert len(catalog['models'])==1066 and len(catalog['dyes'])==132 and len(catalog['emblems']['logos'])==255
files=[]
for part in ['Source','Content/SpellVisuals_v01']:
    for p in (source/part).rglob('*'):
        if p.is_file():
            rel=p.relative_to(source);assert sha(p)==sha(host/rel);files.append((p,rel))
for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor-DAoCVisualBridge.pdb','UnrealEditor.modules']:
    rel=Path('Binaries/Win64')/name;files.append((host/rel,rel))
for p,rel in files:
    dest=installed/rel;old=backup/rel
    if dest.exists() and not old.exists():old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,old)
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(p)==sha(dest)
backup.mkdir(parents=True,exist_ok=True)
if not (backup/'equipment_catalog_v01.json').exists():shutil.copy2(R/'equipment_catalog_v01.json',backup/'equipment_catalog_v01.json')
pending=R/'equipment_catalog_v01.pending.json';shutil.copy2(candidate,pending);os.replace(pending,R/'equipment_catalog_v01.json')
manifest={'installed':True,'at':datetime.datetime.now().isoformat(),'native_checks':proof['checks'],'original_weapon_effects':94,'effect_frames':frames['frames'],'original_holder_samples':frames['measured_original_holders'],'quality_limits':{'accessible':8,'balanced':16,'high':24},'work_modified':False,'server_modified':False,'visual_review':'Gameplay appearance pending; no isolated FPS claim. Rare original controllers retain the limitations of the spell renderer.','catalog_sha256':sha(candidate),'files_sha256':{str(rel):sha(p) for p,rel in files}}
(D/'weapon_fx_installation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print({k:v for k,v in manifest.items() if k!='files_sha256'},flush=True)
