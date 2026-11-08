"""Verify authoritative rest state and analyze recorded original server regeneration."""
import argparse,json,os,shutil,statistics,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest
from central_activation_receipts import verify_files

def verify(workspace,install):
    assert verify_files(workspace)['world_clock_installed']
    source=Path(__file__).resolve().parents[1]
    root=workspace/'RestRegenerationLab/Client'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    project=root/'Godot';project.mkdir(parents=True)
    (project/'project.godot').write_text('[application]\nconfig/name="Private Rest QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf-8')
    inputs={}
    for name in ['player_combat_state.gd','test_player_combat.gd','test_rest_regeneration.gd']:
        p=source/'Godot'/name;inputs[str(p)]=digest(p);shutil.copy2(p,project/name)
    env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    exe=install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'
    states={}
    for script,folder in [('test_player_combat','player_state'),('test_rest_regeneration','rest_regeneration')]:
        (root/'Reports'/folder).mkdir(parents=True)
        r=subprocess.run([str(exe),'--headless','--path',str(project),'--script','res://'+script+'.gd'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        (root/(script+'.log')).write_text(r.stdout,encoding='utf-8');assert r.returncode==0 and 'ERROR:' not in r.stdout,r.stdout
        data=json.loads((root/'Reports'/folder/'godot_tests.json').read_text());assert data['passed'] and not data['failures'];states[script]=data['checks']
    assert states['test_rest_regeneration']==12
    real=next(p for p in reversed(sorted((workspace/'RestRegenerationLab/RealProtocol').glob('*/verified.json'))) if json.loads(p.read_text()).get('passed'))
    samples_path=real.parent/'measurements.json';samples=json.loads(samples_path.read_text());inputs[str(real)]=digest(real);inputs[str(samples_path)]=digest(samples_path)
    result=json.loads(real.read_text());assert result['normal_runtime_unchanged'] and result['database_restored'] and result['normal_shutdown']
    measured={}
    for name,expected in [('standing',1),('sitting',4)]:
        rows=samples[name]['samples']
        gains=[b['endurance']-a['endurance'] for a,b in zip(rows,rows[1:]) if b['endurance']>a['endurance'] and b['endurance']<b['max_endurance']]
        assert len(gains)>=5 and set(gains)=={expected},(name,gains)
        measured[name]=dict(health_interval_seconds=statistics.median(samples[name]['health_intervals']),power_interval_seconds=statistics.median(samples[name]['power_intervals']),endurance_per_tick=expected)
    assert all(digest(Path(p))==h for p,h in inputs.items());verify_files(workspace)
    report=dict(passed=True,state_checks=sum(states.values()),states=states,endurance_measurement_checks=2,measurements=measured,source_inputs=inputs,normal_runtime_modified=False,owner_gameplay_accepted=False)
    proof=root/'verified.json';proof.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return dict(passed=True,state_checks=report['state_checks'],endurance_measurement_checks=2,output=str(root))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['workspace','install']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve())))
