"""Exercise actual target/dialog/merchant widgets without a game login."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent;f=R/'Reports/interactions/native_fixture.json';o=Path(str(f)+'.native.json');start=time.time()
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/'GMCombatTest/NativeHost/BridgeGmHost.uproject'),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeInteractionTest='+str(f),'-nullrhi','-unattended','-nosound','-nosplash']
with (R/'Reports/interactions/native_ui.log').open('w')as log:p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert p.returncode==0 and o.stat().st_mtime>=start
x=json.loads(o.read_text(encoding='utf-8-sig'));print(json.dumps(x));assert x['passed']
