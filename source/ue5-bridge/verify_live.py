"""Exercise the real GM session and retain both sides of the movement evidence."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json
import subprocess
import time
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / 'Reports/live'
DOTNET = str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe')

def read(name):
    try:
        return json.loads((REPORTS / name).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {}

def main():
    started = time.time()
    samples = []
    with (REPORTS / 'live_verification_stdout.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([DOTNET, str(ROOT / 'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),
                                    '--character=BridgeFighter', '--auto-test', '--walk-test'], cwd=ROOT,
                                   stdout=log, stderr=subprocess.STDOUT)
        while process.poll() is None and time.time()-started < 300:
            ue_path = REPORTS / 'unreal_session.json'
            if ue_path.exists() and ue_path.stat().st_mtime >= started:
                samples.append({'unreal': read('unreal_session.json'), 'godot': read('godot_session.json')})
            time.sleep(.5)
        if process.poll() is None:
            (REPORTS / 'logout.request').write_text('logout')
            raise RuntimeError('Verification timed out; normal logout requested. No game process was killed.')
    final = read('godot_session.json')
    good = [s for s in samples if s['unreal'].get('connected') and s['godot'].get('playing')]
    first = next((s for s in good if s['godot'].get('move_commands', 0)>0), None)
    last = next((s for s in reversed(good) if s['godot'].get('move_commands', 0)>0), None)
    displacement = 0
    excursion=0
    if first and last:
        a, b = first['godot']['position_m'], last['godot']['position_m']
        displacement = ((b[0]-a[0])**2 + (b[2]-a[2])**2)**.5
        for sample in good:
            p=sample['godot'].get('position_m',a);excursion=max(excursion,((p[0]-a[0])**2+(p[2]-a[2])**2)**.5)
    shot = REPORTS / 'Ardee_GM_Client.png'
    result = dict(real_server=True, character=final.get('character'),
                  samples=len(good), max_npcs=max((s['unreal'].get('npcs',0) for s in good),default=0),
                  modeled_entities_created=max((s['unreal'].get('modeled_entities_created',0) for s in good),default=0),
                  received_move_commands=final.get('move_commands',0), rejected_commands=final.get('bridge_rejected',0),
                  server_gateway_displacement_m=displacement,
                  server_gateway_excursion_m=excursion,
                  standalone_game=any(s['unreal'].get('standalone_game') for s in good),
                  normal_logout=not final.get('playing',True) and 'protocolo normal' in final.get('status',''),
                  screenshot=shot.exists() and shot.stat().st_mtime>=started,
                  helper_exit_code=process.returncode,
                  first_moving=first, last_moving=last)
    result['navigation_ready']=bool(good) and all(s['unreal'].get('navigation_ready',False) for s in good)
    result['grounded_sample_fraction']=sum(bool(s['unreal'].get('character_grounded')) for s in good)/max(1,len(good))
    result['travelled_metres']=max((s['unreal'].get('travelled_metres',0) for s in good),default=0)
    result['navigation_probe']=next((s['unreal']['navigation_probe'] for s in reversed(good) if 'navigation_probe' in s['unreal']),{})
    frame_samples=[s['unreal']['fps_median'] for s in good if 'fps_median' in s['unreal']]
    if frame_samples:
        result['observed_fps_median']=statistics.median(frame_samples)
        result['observed_fps_median_last_samples']=statistics.median(frame_samples[-20:])
        result['quality']=last['unreal'].get('quality') if last else None
    walking=[s['unreal']['fps_median'] for s in good if s['unreal'].get('auto_walk_active') and 'fps_median' in s['unreal']]
    if walking:result['walking_fps_median']=statistics.median(walking)
    result['performance_acceptable']=result.get('walking_fps_median',0)>=30
    result['passed'] = bool(result['normal_logout'] and result['standalone_game'] and result['screenshot']
                            and result['received_move_commands']>10 and result['rejected_commands']==0
                            and excursion>20 and result['max_npcs']>10 and result['modeled_entities_created']>10
                            and result['helper_exit_code']==0 and result['performance_acceptable'])
    result['passed']=result['passed'] and result['navigation_ready'] and result['grounded_sample_fraction']>.9 and result['navigation_probe'].get('passed',False)
    (REPORTS / 'live_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['first_moving','last_moving']}))
    if not result['passed']:
        raise RuntimeError('Real session verification failed; see live_verification.json')

if __name__=='__main__':
    main()
