from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
import json,shutil,hashlib
R=Path(str(ROOT));D=R/'Reports/release_camera'
checks=json.loads((D/'native/acceptance.json').read_text(encoding='utf-8'));g=json.loads((D/'godot_tests.json').read_text(encoding='utf-8'));assert g['passed']and all(v['passed']for v in checks.values())
source=R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge';target=R/'Client/Plugins/DAoCVisualBridge';assert (R/'Backups/ReleaseCamera_20261101/Binaries').exists()
for name in ['Source','Binaries']:
 shutil.copytree(source/name,target/name,dirs_exist_ok=True)
 for p in (source/name).rglob('*'):
  if p.is_file():assert p.read_bytes()==(target/p.relative_to(source)).read_bytes()
report={'installed':True,'godot_checks':g['checks'],'native_checks':sum(v['checks']for v in checks.values()),'real_release_tested':False,'dll_sha256':hashlib.sha256((target/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll').read_bytes()).hexdigest()}
(D/'install.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
