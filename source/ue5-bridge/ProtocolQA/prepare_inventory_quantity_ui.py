"""Reuse the original Choose Quantity frame, buttons and arrows without editing art."""
import argparse,json,shutil,hashlib,struct
from pathlib import Path

def prepare(workspace,install):
    root=workspace/'InventoryQuantityLab';resources=root/'Resources/QuantityUI_v01';resources.mkdir(parents=True,exist_ok=True)
    source=install/'new-client/godot/content/ui/classic/x4plus'
    rows=[]
    for name in ['dialog_sm.png','buttons.png','arrows.png']:
        src=source/name;dst=resources/name;shutil.copy2(src,dst)
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        assert sha(src)==sha(dst)
        # Add-only private namespace, not referenced by the installed predecessor.
        target=workspace/'Client/Plugins/DAoCVisualBridge/Content/ClassicUI/QuantityUI_v01'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert sha(target)==sha(src)
        else:shutil.copy2(dst,target)
        rows.append(dict(source=str(src),target=str(target),sha256=sha(src),dimensions=struct.unpack('>II',src.read_bytes()[16:24])))
    proof=dict(passed=True,original_art_modified=False,files=rows)
    (root/'resources.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');return proof
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--install',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve(),a.install.resolve())))
