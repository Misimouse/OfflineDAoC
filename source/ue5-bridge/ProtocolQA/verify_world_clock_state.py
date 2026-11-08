"""Exercise clock metadata and the exact installed original time interpolation helper privately."""
import argparse,json,os,re,shutil,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install):
    source=Path(__file__).resolve().parents[1]
    root=workspace/'WorldClockLab/State'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');root.mkdir(parents=True)
    original=install/'new-client/godot/game/net/server.gd'
    text=original.read_text(encoding='utf-8-sig')
    match=re.search(r'^func game_hour\(\) -> float:\n.*?(?=^\S)',text,re.M|re.S)
    assert match,'Exact original helper required'
    helper='extends Node\nvar game_time_ms:int=-1\nvar game_time_at:int=0\nvar day_increment:float=24.0\n'+match.group()
    (root/'original_clock_helper.gd').write_text(helper,encoding='utf-8')
    (root/'project.godot').write_text('[application]\nconfig/name="Private World Clock QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf-8')
    inputs={str(original):digest(original)}
    for name in ['test_world_clock.gd','live_gateway.gd','visual_bridge.gd']:
        p=source/'Godot'/name;inputs[str(p)]=digest(p);shutil.copy2(p,root/name)
    env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    exe=install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'
    run=subprocess.run([str(exe),'--headless','--path',str(root),'--script','res://test_world_clock.gd'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
    (root/'godot.log').write_text(run.stdout,encoding='utf-8')
    assert run.returncode==0 and 'ERROR:' not in run.stdout,run.stdout
    result=json.loads((root/'verified_state.json').read_text());assert result['passed'] and result['checks']==22,result
    assert all(digest(Path(p))==h for p,h in inputs.items())
    result.update(source_inputs=inputs,normal_installation_modified=False)
    (root/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    proof=dict(passed=True,checks=result['checks'],proof=str(root/'verified.json'),proof_sha256=digest(root/'verified.json'))
    (workspace/'WorldClockLab/state.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');return proof
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['workspace','install']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve())))
