"""Parse the gateway against the real autoloads, without starting a session."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import os,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent;I=Path(str(INSTALL))
env=dict(os.environ,DOTNET_ROOT=str(I/'tools/dotnet'),DOTNET_ROOT_X64=str(I/'tools/dotnet'),APPDATA=str(R/'Reports/isolated-save'))
r=subprocess.run([str(I/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(I/'new-client/godot'),'--check-only','--script',str(R/'Godot/live_gateway.gd')],env=env,capture_output=True,text=True,timeout=35,creationflags=subprocess.CREATE_NO_WINDOW)
print(r.stdout,r.stderr);assert r.returncode==0 and 'SCRIPT ERROR' not in r.stderr
