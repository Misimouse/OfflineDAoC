"""Optional 90-second synthetic preview. Start the editor receiver separately.
No account/login options; uses the existing C# decoder against a local fixture.
"""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import os
import socket
import subprocess
from pathlib import Path
from wire_fixture import Fixture

ROOT=Path(__file__).resolve().parent
INSTALL=Path(str(INSTALL))
reports=ROOT/'Reports/preview';reports.mkdir(exist_ok=True,parents=True)
with socket.socket() as probe:probe.bind(('127.0.0.1',19727))
env=dict(os.environ,DOTNET_ROOT=str(INSTALL/'tools/dotnet'),DOTNET_ROOT_X64=str(INSTALL/'tools/dotnet'),
         APPDATA=str(reports/'isolated-save'))
fixture=Fixture();fixture.start()
command=[str(INSTALL/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),
         '--headless','--path',str(INSTALL/'new-client/godot'),'--script',str(ROOT/'Godot/wire_sender.gd'),'--',
         '--port=19727',f'--wire-port={fixture.port}','--duration=90',f'--report={reports / "sender.json"}']
proc=None
try:
    print('Synthetic preview for 90 seconds. No game server/account. Close with Ctrl+C.')
    with (reports/'godot.log').open('w') as log:
        proc=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        proc.wait(timeout=110)
finally:
    if proc is not None and proc.poll() is None:proc.terminate();proc.wait(timeout=10)
    fixture.close()
