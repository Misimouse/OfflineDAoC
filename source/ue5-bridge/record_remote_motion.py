"""Record actual decoded NPC movement, without changing server AI or saves directly."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import subprocess,time,json,sys,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/movement';L=R/'Reports/live'
start=time.time()
with (D/'record_stdout.log').open('w')as log:
 p=subprocess.run([str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--auto-test','--record-motion'],cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=300)
assert p.returncode==0
final=json.loads((L/'godot_session.json').read_text(encoding='utf-8-sig'))
assert not final['playing']and'protocolo normal'in final['status']
trace=D/'server_trace.json';assert trace.stat().st_mtime>=start
shutil.copy2(L/'godot_session.json',D/'record_godot_session.json')
x=final['remote_motion'];x['normal_logout']=True
(D/'record_summary.json').write_text(json.dumps(x,indent=2));print(json.dumps(x))
