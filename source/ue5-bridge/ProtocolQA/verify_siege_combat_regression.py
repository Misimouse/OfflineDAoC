"""Replay existing original combat animation checks against the siege candidate."""
import json,shutil,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest

def verify(workspace,engine):
 root=workspace/'SiegeWorldLab';bp=root/'native_build.json';build=json.loads(bp.read_text());assert build['passed']
 out=root/'CombatRegression'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True);fixture=out/'fixture.json';shutil.copy2(workspace/'Reports/combat_visual/fixture.json',fixture)
 args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),build['project'],'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeCatalog='+str(workspace/'models.json'),'-DaocBridgeCombatVisualTest='+str(fixture),'-nullrhi','-unattended','-nosound','-nosplash','-abslog='+str(out/'engine.log')]
 with (out/'stdout.log').open('w',encoding='utf-8') as log:result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
 report=Path(str(fixture)+'.native.json');assert result.returncode==0 and report.exists(),str(out)
 data=json.loads(report.read_text(encoding='utf-8-sig'));assert data['passed'] and not data['real_server'] and data['checks']>=14,data
 data.update(build_receipt_sha256=digest(bp),normal_runtime_modified=False);(out/'verified.json').write_text(json.dumps(data,indent=2));return dict(passed=True,checks=data['checks'],output=str(out))
