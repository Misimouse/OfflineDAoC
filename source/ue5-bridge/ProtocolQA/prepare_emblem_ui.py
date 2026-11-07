"""Stage the original picker frame and its palette; reuse existing native emblem assets."""
import argparse,json,shutil,struct
from pathlib import Path
from prepare_combined_expansion_data import digest

def prepare(workspace,install):
    source=install/'new-client/godot/content';root=workspace/'EmblemWindowLab';out=root/'Resources/EmblemUI_v01';out.mkdir(parents=True,exist_ok=True)
    frame=source/'ui/classic/x4plus/emblempick.png';palette=source/'emblems/emblems.json';catalog=workspace/'equipment_catalog_v01.json'
    target=out/'emblempick.png';shutil.copy2(frame,target);assert digest(frame)==digest(target)
    size=struct.unpack('>II',target.read_bytes()[16:24]);assert size==(876,1152)
    data=json.loads(palette.read_text());native=json.loads(catalog.read_text())['emblems']
    assert len(data['logos'])==255 and len(data['primary'])==16 and len(data['secondary'])==8 and len(data['masks'])==4
    (out/'picker.json').write_text(json.dumps(dict(version=1,palette=data,assets=native),indent=2),encoding='utf-8')
    proof=dict(passed=True,root=str(out),files={str(p):digest(p) for p in out.iterdir() if p.is_file()},input_hashes={str(p):digest(p) for p in [frame,palette,catalog]},frame_dimensions=size,normal_installation_modified=False,stock_art_modified=False)
    (root/'resources.json').write_text(json.dumps(proof,indent=2));return dict(passed=True,output=str(root/'resources.json'),files=len(proof['files']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--install',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve(),a.install.resolve())))
