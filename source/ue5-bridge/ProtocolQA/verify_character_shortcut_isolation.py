"""Verify per-character quickbar/page persistence in a fresh private project."""
import argparse,json,os,shutil,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install):
    source=Path(__file__).resolve().parents[1]/'Godot';root=workspace/'CrossClassSwitchLab/State'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');project=root/'Project';project.mkdir(parents=True)
    (project/'project.godot').write_text('[application]\nconfig/name="Private character shortcut isolation"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    inputs={str(p):digest(p) for p in source.glob('*.gd')}
    for name in inputs:shutil.copy2(name,project/Path(name).name)
    (root/'Reports/ui_integration').mkdir(parents=True)
    env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    reports=[]
    for test in ['test_classic_ui.gd','test_character_shortcut_isolation.gd']:
        run=subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--audio-driver','Dummy','--path',str(project),'--script','res://'+test],env=env,capture_output=True,text=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
        output=run.stdout+run.stderr;(root/(test+'.log')).write_text(output,encoding='utf-8');assert run.returncode==0 and 'ERROR:' not in output,output
        v=json.loads(next(line for line in output.splitlines() if line.startswith('{') and '"passed"' in line));assert v['passed'] and not v['failures'];reports.append(dict(test=test,checks=v['checks']))
    assert all(digest(Path(p))==h for p,h in inputs.items())
    value=dict(passed=True,reports=reports,source_inputs=inputs,server_started=False,normal_installation_modified=False);(root/'verified.json').write_text(json.dumps(value,indent=2));return dict(passed=True,reports=reports,proof=str(root/'verified.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve())))
