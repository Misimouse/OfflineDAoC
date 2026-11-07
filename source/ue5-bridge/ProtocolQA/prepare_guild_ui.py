"""Stage byte-identical original guild checkbox art under a new private namespace."""
import argparse,json,shutil,struct
from pathlib import Path
from prepare_combined_expansion_data import digest

def prepare(workspace,install):
    source=install/'new-client/godot/content/ui/classic/x4plus/radiobutton1.png'
    root=workspace/'GuildWindowLab';target=root/'Resources/GuildUI_v01/radiobutton1.png';target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target);assert digest(source)==digest(target)
    data=target.read_bytes();assert data.startswith(b'\x89PNG');size=struct.unpack('>II',data[16:24]);assert size[0]==2*size[1]
    proof=dict(passed=True,source=str(source),source_sha256=digest(source),target=str(target),sha256=digest(target),dimensions=size,normal_installation_modified=False,stock_art_modified=False)
    (root/'resources.json').write_text(json.dumps(proof,indent=2));return dict(passed=True,dimensions=size,output=str(root/'resources.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--install',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve(),a.install.resolve())))
