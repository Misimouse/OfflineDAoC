from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import os
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
INSTALL=Path(str(INSTALL))
env=dict(os.environ,DOTNET_ROOT=str(INSTALL/'tools/dotnet'),DOTNET_ROOT_X64=str(INSTALL/'tools/dotnet'),
         APPDATA=str(ROOT/'Reports/model-export-save'))
command=[str(INSTALL/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless',
         '--path',str(INSTALL/'new-client/godot'),'--script',str(ROOT/'Godot/export_all_animations.gd')]
with (ROOT/'Reports/pose_animations/export_all.log').open('w') as log:
    result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200,creationflags=subprocess.CREATE_NO_WINDOW)
log=(ROOT/'Reports/model-export-save/Godot/app_userdata/MMOEngine/logs/godot.log').read_text(errors='replace')
print(log[-2500:]);assert result.returncode==0 and 'BRIDGE_MODEL_EXPORT_PASS' in log
