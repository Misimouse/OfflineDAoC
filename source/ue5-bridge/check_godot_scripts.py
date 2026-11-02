from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import os
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
INSTALL=Path(str(INSTALL))
engine=INSTALL/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'
env=dict(os.environ,DOTNET_ROOT=str(INSTALL/'tools/dotnet'),DOTNET_ROOT_X64=str(INSTALL/'tools/dotnet'),APPDATA=str(ROOT/'Reports/isolated-save'))
for name in ['visual_bridge.gd','decoded_world_adapter.gd','live_observer.gd','proof_sender.gd']:
    result=subprocess.run([str(engine),'--headless','--path',str(ROOT/'Godot'),'--check-only','--script','res://'+name],
                          env=env,cwd=ROOT/'Godot',capture_output=True,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0 and 'SCRIPT ERROR' not in result.stdout+result.stderr,(name,result.stdout,result.stderr)
    print(name,'PARSE_PASS')
