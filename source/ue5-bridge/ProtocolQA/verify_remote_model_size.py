"""Private adapter regression for original zero-size ModelChange packets."""
import argparse,json,os,shutil,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install,installed=False):
    producer=Path(__file__).resolve().parents[1]/'Godot'
    source=workspace/'Godot' if installed else producer
    root=workspace/'RemoteModelRoundtripLab'/('InstalledState' if installed else 'State')/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    project=root/'Project';project.mkdir(parents=True)
    (project/'project.godot').write_text('[application]\nconfig/name="Private remote model regression"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    inputs={str(p):digest(p) for p in source.glob('*.gd')}
    for name in inputs:shutil.copy2(name,project/Path(name).name)
    if installed:
        for test in ['test_remote_model_size.gd','test_remote_player_state.gd','test_player_model_state.gd']:
            shutil.copy2(producer/test,project/test);inputs[str(producer/test)]=digest(producer/test)
    env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    reports=[]
    for test in ['test_remote_model_size.gd','test_remote_player_state.gd','test_player_model_state.gd']:
        run=subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--audio-driver','Dummy','--path',str(project),'--script','res://'+test],env=env,capture_output=True,text=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
        output=run.stdout+run.stderr;(root/(test+'.log')).write_text(output,encoding='utf-8')
        data=json.loads(next(line for line in output.splitlines() if line.startswith('{') and '"passed"' in line))
        reports.append(dict(test=test,exit_code=run.returncode,**data))
    assert all(digest(Path(p))==h for p,h in inputs.items())
    value=dict(passed=all(r['passed'] and r['exit_code']==0 and not r['failures'] for r in reports),reports=reports,source_inputs=inputs,installed_source=installed,server_started=False,normal_installation_modified=False)
    proof=root/'verified.json';proof.write_text(json.dumps(value,indent=2))
    return dict(passed=value['passed'],reports=reports,proof=str(proof))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--installed',action='store_true')
    a=p.parse_args();result=verify(a.workspace.resolve(),a.install.resolve(),a.installed);print(json.dumps(result));raise SystemExit(0 if result['passed'] else 1)
