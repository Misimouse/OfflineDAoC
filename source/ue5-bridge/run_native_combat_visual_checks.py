from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time,sys
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/combat_visual';fixture=D/'fixture.json';output=Path(str(fixture)+'.native.json');started=time.time()
project=R/('Client/DAoCBridgeClient.uproject'if'--installed'in sys.argv else'ProfilingHost/BridgeHost.uproject')
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeCatalog='+str(R/'models.json'),'-DaocBridgeCombatVisualTest='+str(fixture),'-nullrhi','-unattended','-nosound','-nosplash']
with(D/'native_tests.log').open('w')as log:p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=120)
assert p.returncode==0 and output.exists()and output.stat().st_mtime>=started,'No fresh combat visual result'
data=json.loads(output.read_text(encoding='utf-8-sig'));print(json.dumps(data));assert data['passed']
