"""Incremental editor/game-window build in a dedicated bridge-owned host."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
HOST=ROOT/'ProfilingHost';HOST.mkdir(exist_ok=True)
PLUGIN=HOST/'Plugins/DAoCVisualBridge'
shutil.copytree(ROOT/'UnrealPlugin/DAoCVisualBridge',PLUGIN,dirs_exist_ok=True)
project=HOST/'BridgeHost.uproject'
project.write_text(json.dumps(dict(FileVersion=3,EngineAssociation='5.8',Plugins=[dict(Name='DAoCVisualBridge',Enabled=True)])))
command=[str(ENGINE / 'Build/BatchFiles/Build.bat'),'UnrealEditor','Win64','Development',
         '-Project='+str(project),'-plugin='+str(PLUGIN/'DAoCVisualBridge.uplugin'),'-NoHotReloadFromIDE','-WaitMutex']
with (ROOT/'Reports/profile_build.log').open('w') as log:
    result=subprocess.run(command,cwd=HOST,stdout=log,stderr=subprocess.STDOUT)
if result.returncode:raise SystemExit(result.returncode)
if '--build-only' not in sys.argv:
    shutil.copytree(PLUGIN/'Binaries',ROOT/'Client/Plugins/DAoCVisualBridge/Binaries',dirs_exist_ok=True)
print('Incremental bridge plugin build passed.')
