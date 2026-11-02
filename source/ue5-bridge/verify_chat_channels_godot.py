from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import subprocess,os,json,time
from pathlib import Path
R=Path(str(ROOT));I=Path(str(INSTALL / 'new-client'));D=R/'Reports/ui_integration';sdk=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64')
env=dict(os.environ,DOTNET_ROOT=sdk,DOTNET_ROOT_X64=sdk,PATH=sdk+os.pathsep+os.environ['PATH'],APPDATA=str(R/'Reports/isolated-save'))
for script,project,check in [('test_chat_state.gd',R/'Godot',False),('live_gateway.gd',I/'godot',True),('visual_bridge.gd',R/'Godot',True)]:
 start=time.time();cmd=[str(I/'tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(project),'--script',str(R/'Godot'/script),'--quit-after','20']
 if check:cmd.append('--check-only')
 p=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=35,creationflags=subprocess.CREATE_NO_WINDOW)
 (D/(script+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8');assert p.returncode==0 and'SCRIPT ERROR'not in p.stdout+p.stderr,(script,p.stdout,p.stderr)
 if not check:
  q=R/'Reports/chat_channels/godot_tests.json';assert q.exists()and q.stat().st_mtime>=start;data=json.loads(q.read_text(encoding='utf-8'));assert data['passed'];print(json.dumps(data),flush=True)
 else:print(script,'PARSE_PASS',flush=True)
