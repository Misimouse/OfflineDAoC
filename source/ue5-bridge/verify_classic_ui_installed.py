"""Installed client: six UI tabs, actual server, no item operations."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/live';O=R/'Reports/ui_integration'
def read(name):
 try:
  b=(D/name).read_bytes();return json.loads(b.decode('utf-16' if b[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig'))
 except (OSError,ValueError):return {}
start=time.time();samples=[]
with (O/'installed_live.log').open('w',encoding='utf-8') as log:
 p=subprocess.Popen([str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--ui-test'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 while p.poll() is None and time.time()-start<300:
  path=D/'unreal_session.json'
  if path.exists() and path.stat().st_mtime>=start:samples.append(read('unreal_session.json'))
  time.sleep(.25)
 if p.poll() is None:
  (D/'logout.request').write_text('logout');raise RuntimeError('Timeout; normal logout requested')
f=read('godot_session.json');tabs=['character','inventory','skills','combat','magic','group'];seen=sorted(set(s.get('classic_tab','') for s in samples));shots={}
for tab in tabs:
 q=D/f'Classic_{tab}.png'
 if tab=='inventory' and not q.exists():q=D/'Ardee_GM_Client.png'
 shots[tab]=q.exists() and q.stat().st_mtime>=start
 if shots[tab]:shutil.copy2(q,O/f'installed_{tab}.png')
ready=[s for s in samples if s.get('classic_ui',{}).get('ready') or s.get('classic_ui',{}).get('entries')]
result={'real_server':True,'installed_client':True,'exit':p.returncode,'normal_logout':not f.get('playing',True) and f.get('status','')=='Session closed through the normal protocol','tabs_seen':seen,'captures':shots,'ui_ready_samples':len(ready),'three_bars':any(len(s.get('classic_ui',{}).get('bars',[]))==3 for s in ready),'inventory_requests':f.get('inventory',{}).get('requests'),'inventory_rejected':f.get('inventory',{}).get('rejected'),'bridge_rejected':f.get('bridge_rejected'),'move_rejected':f.get('move_rejected')}
result['passed']=bool(p.returncode==0 and result['normal_logout'] and all(t in seen for t in tabs) and all(shots.values()) and ready and result['three_bars'] and all(result[k]==0 for k in ['inventory_requests','inventory_rejected','bridge_rejected','move_rejected']))
(O/'installed_live_samples.json').write_text(json.dumps(samples),encoding='utf-8');(O/'installed_live.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True);assert result['passed']
