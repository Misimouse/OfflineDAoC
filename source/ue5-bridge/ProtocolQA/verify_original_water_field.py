"""Compare staged gameplay water mask with Godot's actual original image sampling."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest

def verify(workspace,install):
    source=Path(__file__).resolve().parents[1]/'Godot/export_original_water_field.gd'
    root=workspace/'WaterMovementLab/OriginalField'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');root.mkdir(parents=True)
    mask=install/'new-client/godot/content/zones/zone207/water.png'
    catalog=workspace/'WaterMovementLab/water_field.json';before={str(p):digest(p) for p in [source,mask,catalog]}
    (root/'project.godot').write_text('[application]\nconfig/name="Private Original Water QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf-8')
    output=root/'original.json';env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    command=[str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(root),'--script',str(source),'--','--water-input='+str(mask),'--water-output='+str(output)]
    with (root/'godot.log').open('w',encoding='utf-8') as log:result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0 and 'ERROR:' not in (root/'godot.log').read_text()
    original=json.loads(output.read_text());data=json.loads(catalog.read_text());expanded=[body for body,length in data['mask_runs'] for _ in range(length)]
    assert original['passed'] and original['mask']==expanded and len(expanded)==65536
    assert all(digest(Path(p))==sha for p,sha in before.items())
    report={'passed':True,'matched_cells':len(expanded),'source_inputs':before,'original_sha256':digest(output),'production_modified':False,'server_started':False}
    (root/'verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return {'passed':True,'matched_cells':65536,'output':str(root)}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(verify(args.workspace.resolve(),args.install.resolve())))
