"""Exercise travel coverage and stale catalogue rejection in an isolated Godot project."""
import argparse,json,os,shutil,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install):
    source=Path(__file__).resolve().parents[1]/'Godot'
    out=workspace/'LiveRidingLab/TravelTests'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    (out/'project.godot').write_text('[application]\nconfig/name="Private Travel Coverage QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf-8')
    paths=[source/'live_travel_routes.gd',source/'test_live_travel_routes.gd',source/'inventory_state.gd',source/'interaction_state.gd',workspace/'LiveRidingLab/travel_routes.json'];inputs={str(p):digest(p) for p in paths}
    for p in paths:shutil.copy2(p,out/p.name)
    env=dict(os.environ,APPDATA=str(out/'AppData'),LOCALAPPDATA=str(out/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    exe=install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'
    run=subprocess.run([str(exe),'--headless','--path',str(out),'--script','res://test_live_travel_routes.gd'],env=env,capture_output=True,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    text=run.stdout+run.stderr;(out/'godot.log').write_text(text,encoding='utf-8');assert run.returncode==0 and 'ERROR:' not in text,text
    result=next(json.loads(line) for line in text.splitlines() if line.startswith('{') and '"passed"' in line)
    assert result['passed'] and result['checks']>=29 and all(digest(Path(p))==sha for p,sha in inputs.items())
    result.update(source_inputs=inputs,normal_installation_modified=False)
    (out/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return dict(passed=True,checks=result['checks'],output=str(out))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','install']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve())))
