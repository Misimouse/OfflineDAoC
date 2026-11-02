from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import hashlib,json,shutil,datetime
from pathlib import Path
R=Path(str(ROOT))
source=R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge';target=R/'Client/Plugins/DAoCVisualBridge'
checks=json.loads((R/'Reports/combat_visual/activation/acceptance.json').read_text(encoding='utf-8'))
assert all(v['passed'] for v in checks.values())
for folder in ['Source','Binaries']:
    assert (R/'Backups/CombatVisual_Activation_20261101'/folder).exists()
    shutil.copytree(source/folder,target/folder,dirs_exist_ok=True)
files={}
for path in (source/'Source').rglob('*'):
    if path.is_file():
        out=target/path.relative_to(source);assert path.read_bytes()==out.read_bytes()
for path in (source/'Binaries').rglob('*'):
    if path.is_file():
        out=target/path.relative_to(source);assert path.read_bytes()==out.read_bytes();files[str(path.relative_to(source))]=hashlib.sha256(out.read_bytes()).hexdigest()
report={'installed':True,'native_checks':sum(v['checks']for v in checks.values()),'binaries':files,'launch_target':'UnrealEditor.exe -game','shipping_updated':False,'real_visual_combat_session':False,'at':datetime.datetime.now().isoformat()}
(R/'Reports/combat_visual/activation/install.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
