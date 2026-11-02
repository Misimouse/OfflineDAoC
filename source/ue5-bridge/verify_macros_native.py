from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time
from pathlib import Path
R=Path(str(ROOT));D=R/'Reports/macros';f=D/'fixture.json';out=Path(str(f)+'.native.json');start=time.time()
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/'GMCombatTest/NativeHost/BridgeGmHost.uproject'),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeClassicTest='+str(f),'-DaocBridgeCatalog='+str(R/'models.json'),'-nullrhi','-unattended','-nosound','-nosplash']
with(D/'native_tests.log').open('w',encoding='utf-8')as log:p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=110)
assert p.returncode==0 and out.exists() and out.stat().st_mtime>=start,(p.returncode,'No new native UI result')
x=json.loads(out.read_text(encoding='utf-8-sig'));print(json.dumps(x),flush=True);assert x['passed']
