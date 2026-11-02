"""Replay decoded Godot snapshots through actual UE actors; never logs in."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent
fixture=R/'Reports/entities/godot_lifecycle.json'
output=Path(str(fixture)+'.native.json')
started=time.time()
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/'Client/DAoCBridgeClient.uproject'),'/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba','-game','-DaocBridge','-DaocBridgeEntityTest='+str(fixture),'-nullrhi','-unattended','-nosound','-nosplash']
with (R/'Reports/entities/native_replay.log').open('w')as log:
 result=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert result.returncode==0 and output.stat().st_mtime>=started,'Missing fresh native replay'
report=json.loads(output.read_text(encoding='utf-8-sig'))
print(json.dumps(report));assert report['passed']
