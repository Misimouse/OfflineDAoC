"""Recheck existing inventory and canonical use contracts for native item shortcuts."""
import argparse,json,os,shutil,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install):
    source=Path(__file__).resolve().parents[1]/'Godot';root=workspace/'ItemShortcutsLab/Compatibility'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');project=root/'Project';project.mkdir(parents=True)
    (project/'project.godot').write_text('[application]\nconfig/name="Private item shortcut compatibility"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    inputs={str(p):digest(p) for p in source.glob('*.gd')}
    for p in source.glob('*.gd'):shutil.copy2(p,project/p.name)
    for name in ['inventory','inventory_rejection','ui_integration']:(root/'Reports'/name).mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    reports=[]
    for name in ['test_inventory.gd','test_inventory_denial.gd','test_classic_ui.gd','test_consumable_details.gd']:
        process=subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--audio-driver','Dummy','--path',str(project),'--script','res://'+name],env=env,capture_output=True,text=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
        text=process.stdout+process.stderr;(root/(name+'.log')).write_text(text,encoding='utf-8');assert process.returncode==0 and 'ERROR:' not in text,text
        folder={'test_inventory.gd':'inventory','test_inventory_denial.gd':'inventory_rejection','test_classic_ui.gd':'ui_integration'}.get(name)
        value=json.loads((root/'Reports'/folder/'godot_tests.json').read_text()) if folder else json.loads(next(line for line in text.splitlines() if line.startswith('{') and '"passed"' in line))
        assert value['passed'] and not value['failures'];reports.append(dict(test=name,checks=value['checks']))
    assert all(digest(Path(p))==h for p,h in inputs.items())
    result=dict(passed=True,reports=reports,source_inputs=inputs,server_started=False,normal_installation_modified=False);(root/'verified.json').write_text(json.dumps(result,indent=2));return dict(passed=True,reports=reports,proof=str(root/'verified.json'))
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(verify(args.workspace.resolve(),args.install.resolve())))
