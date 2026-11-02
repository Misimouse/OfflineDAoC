from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
import subprocess,json,sys
R=Path(__file__).resolve().parent;D=R/'Reports/training_staff_fx_pets';installed='--installed' in sys.argv
out=D/('weapon_fx_installed_native.json' if installed else 'weapon_fx_native.json');out.unlink(missing_ok=True)
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/('Client/DAoCBridgeClient.uproject' if installed else 'GMCombatTest/NativeHost/BridgeGmHost.uproject')),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeCatalog='+str(R/'models.json'),'-DaocBridgeEquipmentCatalog='+str(R/('equipment_catalog_v01.json' if installed else 'equipment_catalog_weapon_fx_candidate.json')),'-DaocBridgeSpellVisualAcceptance='+str(out),'-DaocBridgeWeaponVisualTest','-nullrhi','-unattended','-nosound','-nosplash']
with (D/('weapon_fx_installed_test.log' if installed else 'weapon_fx_native_test.log')).open('w',encoding='utf-8') as log:
 p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert p.returncode==0 and out.exists(),p.returncode
proof=json.loads(out.read_text(encoding='utf-8-sig'));print(proof,flush=True);assert proof['passed'],proof
