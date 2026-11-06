"""Run authoritative live riding state checks in a fresh headless project."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
from prepare_combined_expansion_data import digest

def verify(workspace,install):
    source=Path(__file__).resolve().parents[1]/'Godot'
    root=workspace/'LiveRidingLab/GatewayTest'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');root.mkdir(parents=True)
    (root/'project.godot').write_text('[application]\nconfig/name="Private Live Riding QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf-8')
    inputs={}
    for name in ['live_riding_state.gd','test_live_riding_gateway.gd','live_gateway.gd','movement_flags_state.gd']:
        path=source/name;inputs[str(path)]=digest(path);shutil.copy2(path,root/name)
    env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    exe=install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'
    process=subprocess.run([str(exe),'--headless','--path',str(root),'--script','res://test_live_riding_gateway.gd'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    (root/'godot.log').write_text(process.stdout,encoding='utf-8')
    assert process.returncode==0 and 'ERROR:' not in process.stdout,process.stdout
    report=next(json.loads(line) for line in process.stdout.splitlines() if line.startswith('{') and '"passed"' in line)
    assert report['passed'] and report['checks']>=8 and all(digest(Path(p))==sha for p,sha in inputs.items())
    report.update(source_inputs=inputs,normal_installation_modified=False,server_started=False)
    (root/'verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return {'passed':True,'checks':report['checks'],'output':str(root)}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(verify(args.workspace.resolve(),args.install.resolve())))
