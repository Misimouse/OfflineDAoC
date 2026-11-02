from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
import subprocess,os
R=Path(__file__).resolve().parent;G=Path(str(INSTALL / 'new-client'));sdk=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64')
env=dict(os.environ,DOTNET_ROOT=sdk,DOTNET_ROOT_X64=sdk,APPDATA=str(R/'Reports/training_staff_fx_pets/isolated-export'))
with (R/'Reports/training_staff_fx_pets/emblem_patterns_export.log').open('w',encoding='utf-8') as log:
 p=subprocess.run([str(G/'tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(G/'godot'),'--script',str(R/'Godot/export_emblem_patterns.gd')],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
assert p.returncode==0
