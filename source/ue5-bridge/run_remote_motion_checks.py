from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import subprocess,time,json,sys
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/movement';trace=D/'server_trace.json';output=Path(str(trace)+'.motion-results.json');start=time.time()
project=R/('Client/DAoCBridgeClient.uproject'if'--installed'in sys.argv else'ProfilingHost/BridgeHost.uproject')
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeMotionTest='+str(trace),'-nullrhi','-unattended','-nosound','-nosplash']
with (D/'native_tests.log').open('w')as log:p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert p.returncode==0 and output.stat().st_mtime>=start,'Missing fresh movement result'
x=json.loads(output.read_text(encoding='utf-8-sig'));print(json.dumps(x));assert x['passed']
