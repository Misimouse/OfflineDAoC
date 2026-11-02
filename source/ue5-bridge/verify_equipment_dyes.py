from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
import subprocess,json,time,sys
R=Path(__file__).resolve().parent
D=R/'Reports/training_staff_fx_pets'
fixture=D/'dye_fixture.json'
out=Path(str(fixture)+'.native.json')
out.unlink(missing_ok=True)
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/('Client/DAoCBridgeClient.uproject' if '--installed' in sys.argv else 'GMCombatTest/NativeHost/BridgeGmHost.uproject')),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeCatalog='+str(R/'models.json'),'-DaocBridgeEquipmentCatalog='+str(R/('equipment_catalog_v01.json' if '--installed' in sys.argv else 'equipment_catalog_appearance_candidate.json')),'-DaocBridgeEquipmentTest='+str(fixture),'-DaocBridgeDyeEquipmentTest','-DaocBridgeFlexibleEquipmentTest','-nullrhi','-unattended','-nosound','-nosplash']
with (D/'dye_final_test.log').open('w',encoding='utf-8') as log:
 p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert p.returncode==0 and out.exists(),p.returncode
proof=json.loads(out.read_text(encoding='utf-8-sig'));assert proof['passed'],proof
(D/('dye_installed_native.json' if '--installed' in sys.argv else 'dye_native.json')).write_text(json.dumps(proof,indent=2),encoding='utf-8')
print(proof,flush=True)
