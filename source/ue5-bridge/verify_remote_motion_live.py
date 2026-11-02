"""Observe real, visible NPC motion while the GM stays still; normal logout."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time,math,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/movement';L=R/'Reports/live';start=time.time();samples=[]
def read(path):
 try:return json.loads(path.read_text(encoding='utf-8-sig'))
 except (ValueError,OSError):return {}
with (D/'live_stdout.log').open('w')as log:
 p=subprocess.Popen([str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--motion-test'],cwd=R,stdout=log,stderr=subprocess.STDOUT)
 while p.poll()is None and time.time()-start<300:
  f=L/'unreal_session.json'
  if f.exists()and f.stat().st_mtime>=start:samples.append({'unreal':read(f),'godot':read(L/'godot_session.json')})
  time.sleep(.2)
 if p.poll()is None:
  (L/'logout.request').write_text('logout');raise RuntimeError('Timeout; normal logout requested. No game process killed.')
f=D/'live_visual_samples.json';assert f.stat().st_mtime>=start
visual=read(f);same=0;moved=0;maximum=0;ids=set()
for a,b in zip(visual,visual[1:]):
 if a['id']!=b['id']:continue
 ids.add(a['id'])
 step=math.dist(a['visual_m'],b['visual_m'])
 if a['corrections']==b['corrections']:maximum=max(maximum,step)
 if a['seq']==b['seq']and a['active']and b['active']and not a['blocked']and not b['blocked']:
  same+=1;moved+=int(step>.001)
final=read(L/'godot_session.json');shot=L/'Ardee_GM_Client.png';capture=shot.exists()and shot.stat().st_mtime>=start
if capture:shutil.copy2(shot,D/'Moving_NPC_GM.png')
result={'real_server':True,'normal_logout':not final.get('playing',True)and'protocolo normal'in final.get('status',''),'helper_exit_code':p.returncode,'visual_samples':len(visual),'tracked_ids':sorted(ids),'same_packet_active_pairs':same,'moving_without_new_packet_pairs':moved,'max_regular_observed_step_m':maximum,'bridge_rejected':final.get('bridge_rejected',0),'move_rejected':final.get('move_rejected',0),'screenshot':capture,'max_remote_entities':max((s['unreal'].get('remote_motion',{}).get('entities',0)for s in samples),default=0),'max_remote_moving_entities':max((s['unreal'].get('remote_motion',{}).get('moving',0)for s in samples),default=0),'max_packet_heading_error_degrees':max((s['unreal'].get('npc_heading_error_degrees_max',0)for s in samples),default=999)}
cpu=[s['unreal'].get('remote_motion',{}).get('last_cpu_ms',0)for s in samples if s['unreal'].get('test_elapsed',0)>8 and s['godot'].get('playing') and s['unreal'].get('remote_motion',{}).get('entities',0)>0]
if cpu:
 import statistics
 result['movement_cpu_median_ms']=statistics.median(cpu);result['movement_cpu_p95_ms']=sorted(cpu)[min(len(cpu)-1,int(len(cpu)*.95))]
result['passed']=bool(result['normal_logout']and p.returncode==0 and moved>50 and same>50 and moved/same>.8 and maximum<1.5 and result['bridge_rejected']==0 and result['move_rejected']==0 and capture and result['max_remote_moving_entities']>3 and result['max_packet_heading_error_degrees']<.01)
(D/'live_session_samples.json').write_text(json.dumps(samples));(D/'live_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));assert result['passed']
