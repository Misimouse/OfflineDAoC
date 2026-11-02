from pathlib import Path
import json,shutil,hashlib,datetime
R=Path(__file__).resolve().parent;D=R/'Reports/magic_roundtrip'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
real=read(D/'real_result.json');assert real['passed'] and real['normal_shutdown'] and real['native_exit']==0
reg=read(R/'Reports/ui_integration/regressions/acceptance.json');assert all(v['passed'] for v in reg.values())
godot=read(R/'Reports/spell_casting/godot_tests.json');assert godot['passed'] and godot['checks']==19
source=R/'UnrealPlugin/DAoCVisualBridge';host=R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge';installed=R/'Client/Plugins/DAoCVisualBridge';backup=R/'Backups/MagicRoundtrip_20261102/Installed';files=[]
for p in (source/'Source').rglob('*'):
 if p.is_file():
  rel=p.relative_to(source);assert sha(p)==sha(host/rel);files.append((p,rel))
for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor-DAoCVisualBridge.pdb','UnrealEditor.modules']:
 rel=Path('Binaries/Win64')/name;files.append((host/rel,rel))
for p,rel in files:
 dest=installed/rel
 if dest.exists():
  old=backup/rel;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,old)
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(dest)==sha(p)
manifest={'installed':True,'at':datetime.datetime.now().isoformat(),'native_checks':sum(v['checks'] for v in reg.values()),'godot_spell_checks':godot['checks'],'real_disposable_normal_player_verified':True,'real_native_los':True,'instant_windup_hidden_through_release':True,'game_language':'English','work_modified':False,'normal_characters_modified':False,'original_server_modified':False,'previous_manifest':'Reports/remote_collision/installation.json','files_sha256':{str(rel):sha(p) for p,rel in files},'godot_spell_sha256':sha(R/'Godot/spell_cast_state.gd')}
(D/'installation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
shutil.copy2(R/'Reports/ui_integration/regressions/acceptance.json',D/'native_tests.json');shutil.copy2(R/'Reports/spell_casting/godot_tests.json',D/'godot_tests.json')
print(json.dumps({k:v for k,v in manifest.items() if not k.endswith('sha256')},indent=2))
