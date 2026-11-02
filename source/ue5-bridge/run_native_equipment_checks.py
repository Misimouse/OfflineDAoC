from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time,sys
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/equipment';D.mkdir(exist_ok=True)
samples=json.loads((R/'Reports/pose_animations/visual_samples.json').read_text());ready=next(s['unreal']for s in samples if s['unreal'].get('inventory',{}).get('ready')and s['unreal'].get('player_status',{}).get('ready'))
fixture=D/'fixture.json';fixture.write_text(json.dumps({'inventory':ready['inventory'],'player_status':ready['player_status']}));output=Path(str(fixture)+'.native.json');started=time.time()
project=R/('Client/DAoCBridgeClient.uproject'if'--installed'in sys.argv else'ProfilingHost/BridgeHost.uproject')
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeCatalog='+str(R/'models.json'),'-DaocBridgeEquipmentCatalog='+str(R/'equipment_catalog_v01.json'),'-DaocBridgeEquipmentTest='+str(fixture),'-nullrhi','-unattended','-nosound','-nosplash']
with(D/'native_tests.log').open('w')as log:p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=120)
assert p.returncode==0 and output.exists()and output.stat().st_mtime>=started,'No fresh equipment result'
data=json.loads(output.read_text(encoding='utf-8-sig'));print(json.dumps(data));assert data['passed']
