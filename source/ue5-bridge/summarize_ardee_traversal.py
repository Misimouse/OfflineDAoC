"""Consolidate measured physics, real door protocol and observed rendering results."""
import json,math,statistics
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/navigation/traversal';L=R/'Reports/live'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
suites=[read(D/(name+'_summary.json'))for name in ['routes','closed_routes','occupied_routes','swing_routes']]
live={name:read(L/(name+'_door_live_verification.json'))for name in ['tavern','shack']}
observations={}
for name in live:
    samples=read(L/(name+'_door_live_samples.json'))
    idle=[s for s in samples if 13.6<s['unreal'].get('test_elapsed',0)<15.6 or 23.5<s['unreal'].get('test_elapsed',0)<28]
    error=max(math.dist(s['unreal']['position_m'],s['godot']['position_m'])for s in idle)
    live[name]['idle_position_error_m']=error
    assert error<.1,(name,'movement synchronization')
    observations[name]={'last_fps_median':statistics.median(s['unreal'].get('fps_median',0)for s in samples[-25:]),
        'max_received_npcs':max(s['unreal'].get('npcs',0)for s in samples),'quality':'balanced','resolution':[1920,1080],
        'controlled_benchmark':False}
physical=read(D/'routes.json.results.json')
reference=next(row for row in physical['routes']if row['id']=='running_speed_reference')
result={'map':'Ardee_Nwiro_Prueba','physics_suites':suites,'physics_checks':sum(s['routes']for s in suites),
    'real_sessions':live,'base_running_speed_mps':reference['peak_speed_mps'],'door_interaction':'E opens; server timer closes',
    'rendering_observations':observations,'rendering_followup':'The original large tavern remains substantially slower than the remodeled house; profile its rendering separately.',
    'build_complete':'BUILD SUCCESSFUL'in(R/'Reports/native_build.log').read_text(errors='replace'),
    'scope':'Ardee buildings, three nearby huts, the nearby bridge and measured staircase; not a certification of all Connacht or other regions.'}
result['movement_passed']=all(s['passed']for s in suites)and all(s['passed']for s in live.values())
(D/'final_summary.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in ['real_sessions','physics_suites']}))
assert result['movement_passed']
