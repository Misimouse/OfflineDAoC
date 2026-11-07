"""Retain existing inventory/merchant/armour-denial semantics in a fresh project."""
import argparse,json,os,shutil,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install):
    source=Path(__file__).resolve().parents[1]/'Godot'
    root=workspace/'WeaponPoisonLab/Compatibility'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');project=root/'Project';project.mkdir(parents=True)
    (project/'project.godot').write_text('[application]\nconfig/name="Private inventory compatibility QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    inputs={}
    for name in ['inventory_state.gd','interaction_state.gd','test_inventory.gd','test_inventory_denial.gd','test_item_handover.gd','test_item_handover_gateway.gd','live_gateway.gd','visual_bridge.gd']:
        p=source/name;inputs[str(p)]=digest(p);shutil.copy2(p,project/name)
    env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    reports={}
    for script,folder in [('test_inventory.gd','inventory'),('test_inventory_denial.gd','inventory_rejection'),('test_item_handover.gd','handover'),('test_item_handover_gateway.gd','gateway')]:
        target=root/'Reports'/folder;target.mkdir(parents=True)
        r=subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(project),'--script','res://'+script],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        (root/(script+'.log')).write_text(r.stdout,encoding='utf-8');assert r.returncode==0 and 'ERROR:' not in r.stdout,r.stdout
        value=json.loads((target/'godot_tests.json').read_text()) if (target/'godot_tests.json').exists() else next(json.loads(line) for line in r.stdout.splitlines() if line.startswith('{') and '"passed"' in line);assert value['passed'] and not value['failures'];reports[folder]=value
    assert all(digest(Path(p))==h for p,h in inputs.items())
    report=dict(passed=True,source_inputs=inputs,reports=reports,normal_installation_modified=False,server_started=False)
    (root/'verified.json').write_text(json.dumps(report,indent=2));return dict(passed=True,checks={k:v['checks'] for k,v in reports.items()},output=str(root))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--install',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve())))
