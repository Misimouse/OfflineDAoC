"""Stage the existing original realm-war maps and frame without changing their artwork."""
import argparse,json,shutil,struct
from pathlib import Path
from prepare_combined_expansion_data import digest

def prepare(workspace,install):
    original=install/'new-client/godot/content/ui/warmap';root=workspace/'RvRWindowsLab';resources=root/'Resources/RealmWarUI_v01';resources.mkdir(parents=True,exist_ok=True)
    files=[]
    for name in ['warmap.json','albmap.png','midmap.png','hibmap.png','map_icons.png','realm_symb.png','frame.png']:
        source=install/'new-client/godot/content/ui/classic/x4plus/interact.png' if name=='frame.png' else original/name
        staged=resources/name;shutil.copy2(source,staged);assert digest(source)==digest(staged)
        target=workspace/'Client/Plugins/DAoCVisualBridge/Content/ClassicUI/RealmWarUI_v01'/name;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert digest(target)==digest(source)
        else:shutil.copy2(staged,target)
        row=dict(source=str(source),target=str(target),sha256=digest(source),bytes=source.stat().st_size)
        if name.endswith('.png'):row['dimensions']=struct.unpack('>II',source.read_bytes()[16:24])
        files.append(row)
    data=json.loads((resources/'warmap.json').read_text());assert set(data['pages'])=={'alb','mid','hib'}
    result=dict(passed=True,original_art_modified=False,world_map_modified=False,files=files)
    (root/'resources.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--install',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve(),a.install.resolve())))
