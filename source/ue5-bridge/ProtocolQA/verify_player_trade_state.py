"""Run inactive player-trade identity regressions in a disposable Godot project."""
import argparse,json,os,shutil,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install,controller=False):
    source=Path(__file__).resolve().parents[1]/'Godot'
    root=workspace/('PlayerTradeLab/Controller' if controller else 'PlayerTradeLab/State')/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    project=root/'Project';project.mkdir(parents=True)
    (project/'project.godot').write_text('[application]\nconfig/name="Private trade state"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    inputs={}
    names=['player_trade_state.gd','test_player_trade_state.gd','inventory_state.gd']
    if controller:names+=['player_trade_controller.gd','test_player_trade_controller.gd']
    for name in names:
        p=source/name;inputs[str(p)]=digest(p);shutil.copy2(p,project/name)
    env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    run=subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--audio-driver','Dummy','--path',str(project),'--script','res://test_player_trade_controller.gd' if controller else 'res://test_player_trade_state.gd'],env=env,capture_output=True,text=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
    output=run.stdout+run.stderr;(root/'godot.log').write_text(output,encoding='utf-8')
    try:result=json.loads(next(line for line in output.splitlines() if line.startswith('{') and '"passed"' in line))
    except StopIteration:raise AssertionError(str(root/'godot.log'))
    result.update(exit_code=run.returncode,source_inputs=inputs,server_started=False,normal_installation_modified=False)
    assert all(digest(Path(p))==sha for p,sha in inputs.items())
    proof=root/'verified.json';proof.write_text(json.dumps(result,indent=2))
    assert result['passed'] and run.returncode==0 and not result['failures'],str(proof)
    return dict(passed=True,checks=result['checks'],proof=str(proof),installed=False)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--controller',action='store_true')
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.controller)))
