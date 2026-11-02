from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import subprocess
from pathlib import Path
R=Path(str(ROOT))
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/'GMCombatTest/NativeHost/BridgeGmHost.uproject'),'-run=pythonscript','-script='+str(R/'import_connacht_missing_unreal.py'),'-nullrhi','-unattended','-nosound','-nosplash']
with (R/'Reports/connacht_models/import.log').open('w',encoding='utf-8')as log:p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=240)
print('Import exit',p.returncode);assert p.returncode==0
