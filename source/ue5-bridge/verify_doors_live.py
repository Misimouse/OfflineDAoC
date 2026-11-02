"""Real protocol proof: close, request opening, cross, close, return and logout."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time,sys,math
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/live'
DOTNET=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe')
def read(name):
    try:return json.loads((D/name).read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return {}
def main():
    shack='--shack'in sys.argv;target_id=207033603 if shack else 207033701;prefix='shack_'if shack else 'tavern_'
    catalog=json.loads((R/'collision_catalog.json').read_text());fixture=next(f for m in catalog['models'].values()for f in m.get('door_fixtures',[])if target_id in f['groups'].values())
    plane=1250.6-fixture['position_m'][2]if shack else fixture['position_m'][2]-1270.9
    start=time.time();samples=[]
    with (D/'door_test_stdout.log').open('w')as log:
        process=subprocess.Popen([DOTNET,str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--auto-test','--shack-door-test'if shack else '--door-test'],cwd=R,stdout=log,stderr=subprocess.STDOUT)
        while process.poll()is None and time.time()-start<300:
            path=D/'unreal_session.json'
            if path.exists() and path.stat().st_mtime>=start:
                u=read('unreal_session.json');g=read('godot_session.json')
                if u.get('door_auto_test') and g.get('playing'):samples.append(dict(unreal=u,godot=g))
            time.sleep(.2)
        if process.poll()is None:
            (D/'logout.request').write_text('logout');raise RuntimeError('Timed out. Normal logout requested; no game process killed.')
    final=read('godot_session.json');rows=[s['unreal']for s in samples]
    closed_before=[s for s in rows if 6.3<s.get('test_elapsed',0)<7.9 and any(d['id']==target_id and not d['open']and d['alpha']<.05 for d in s.get('doors',[]))]
    closed_inside=[s for s in rows if 16.3<s.get('test_elapsed',0)<17.9 and any(d['id']==target_id and not d['open']and d['alpha']<.05 for d in s.get('doors',[]))]
    returned=[s for s in rows if 23<s.get('test_elapsed',0)<29]
    result=dict(real_server=True,character=final.get('character'),samples=len(rows),normal_logout=not final.get('playing',True)and 'protocolo normal'in final.get('status',''),
        gateway_door_requests=final.get('door_requests',0),gateway_door_events=final.get('door_events',0),
        native_door_requests=max((s.get('door_requests',0)for s in rows),default=0),
        native_state_changes=max((s.get('door_state_changes',0)for s in rows),default=0),
        maximum_progress_m=max((s.get('door_test_progress_m',0)for s in rows),default=0),
        closed_outside_samples=len(closed_before),closed_outside_max_progress_m=max((s['door_test_progress_m']for s in closed_before),default=999),
        closed_inside_samples=len(closed_inside),closed_inside_min_progress_m=min((s['door_test_progress_m']for s in closed_inside),default=-999),
        returned_metres=min((abs(s['door_test_progress_m'])for s in returned),default=999),
        received_move_commands=final.get('move_commands',0),rejected_commands=final.get('bridge_rejected',0),
        run_speed_mps=max((s.get('run_speed_mps',0)for s in rows),default=0),helper_exit_code=process.returncode)
    result['native_peak_speed_mps']=max((s.get('peak_movement_speed_mps',0)for s in rows),default=0)
    result['gateway_peak_speed_mps']=final.get('peak_move_speed_mps',0)
    result['door_id']=target_id;result['door_plane_progress_m']=plane
    idle=[s for s in samples if (13.6<s['unreal'].get('test_elapsed',0)<15.6 or 23.5<s['unreal'].get('test_elapsed',0)<28)]
    result['idle_position_error_m']=max((math.dist(s['unreal']['position_m'],s['godot']['position_m'])for s in idle),default=999)
    result['move_rejected']=final.get('move_rejected',0);result['server_speed_percent']=final.get('max_speed_percent')
    result['passed']=bool(result['normal_logout']and result['helper_exit_code']==0 and result['gateway_door_requests']>=2 and result['gateway_door_events']>=4 and
        result['native_state_changes']>=2 and result['maximum_progress_m']>6 and result['returned_metres']<.3 and result['closed_outside_samples']>0 and
        result['closed_outside_max_progress_m']<plane-.05 and result['closed_inside_samples']>0 and result['closed_inside_min_progress_m']>plane+.05 and result['rejected_commands']==0 and result['move_rejected']==0 and result['idle_position_error_m']<.1)
    (D/(prefix+'door_live_samples.json')).write_text(json.dumps(samples));(D/(prefix+'door_live_verification.json')).write_text(json.dumps(result,indent=2));print(json.dumps(result))
    if not result['passed']:raise RuntimeError('Door protocol verification failed; inspect the saved samples.')
if __name__=='__main__':main()
