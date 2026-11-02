from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/viewport_map';fixture=D/'fixture.json';out=Path(str(fixture)+'.native.json');start=time.time()
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/'GMCombatTest/NativeHost/BridgeGmHost.uproject'),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeViewportTest='+str(fixture),'-windowed','-ResX=1280','-ResY=720','-d3d11','-unattended','-nosound','-nosplash']
with (D/'native_tests.log').open('w',encoding='utf-8') as log:p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=160,creationflags=subprocess.CREATE_NO_WINDOW)
assert p.returncode==0 and out.exists() and out.stat().st_mtime>=start,(p.returncode,'No new native chat result')
shot=Path(str(fixture)+'.png');assert shot.exists() and shot.stat().st_mtime>=start,'No fresh native viewport screenshot'
d=json.loads(out.read_text(encoding='utf-8-sig'));print(json.dumps(d));assert d['passed']
