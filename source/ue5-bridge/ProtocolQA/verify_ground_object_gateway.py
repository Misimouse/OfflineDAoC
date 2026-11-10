"""Exercise actual ground routing and existing movement/control regressions without a server."""
import argparse,json,shutil,subprocess
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install):
    source=Path(__file__).resolve().parents[1]/'Godot';lab=workspace/'GroundObjectRuntimeLab';project=lab/'GatewayProject';project.mkdir(exist_ok=True)
    inputs={str(p):digest(p) for p in source.glob('*.gd')}
    for p in source.glob('*.gd'):shutil.copy2(p,project/p.name)
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Private ground gateway"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    shutil.copy2(workspace/'OriginalControlsLab/StateProject/original_weapon_reference.gd',project/'original_weapon_reference.gd')
    reports=[]
    for name,minimum in [('test_ground_object_gateway.gd',15),('test_weapon_sprint_gateway.gd',8),('test_personal_torch_gateway.gd',261),('test_live_riding_gateway.gd',6),('test_remote_player_state.gd',69)]:
        r=subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--audio-driver','Dummy','--path',str(project),'--script',str(project/name),'--quit-after','120'],capture_output=True,text=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        text=r.stdout+r.stderr;(lab/(name+'.log')).write_text(text,encoding='utf-8');assert r.returncode==0 and 'ERROR:' not in text,str(lab/(name+'.log'))
        data=json.loads(next(line for line in text.splitlines() if line.startswith('{')));assert data['passed'] and data['checks']>=minimum,data;reports.append(dict(test=name,checks=data['checks']))
    assert all(digest(Path(p))==h for p,h in inputs.items())
    (lab/'gateway_tests.json').write_text(json.dumps(dict(passed=True,reports=reports,source_inputs=inputs,installed=False,server_started=False),indent=2))
    return dict(passed=True,reports=reports)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ['workspace','install']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve())))
