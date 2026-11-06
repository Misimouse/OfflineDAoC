"""Give the private riding host one writable asset namespace; all approved libraries remain junctions."""
import argparse,json,shutil,subprocess
from pathlib import Path

def prepare(workspace):
    private=workspace/'LiveRidingLab/NativeHost/Plugins/DAoCVisualBridge/Content';central=workspace/'Client/Plugins/DAoCVisualBridge/Content'
    assert private.absolute().is_relative_to((workspace/'LiveRidingLab').absolute()) and central.is_dir()
    if private.is_junction():
        assert private.resolve()==central.resolve()
        private.rmdir() # Remove this checked junction only; never recurse into its shared target.
    private.mkdir(parents=True,exist_ok=True)
    quote=lambda p:"'"+str(p).replace("'","''")+"'"
    count=0
    for source in central.iterdir():
        assert source.name!='LiveRiding_v01','Riding delivery is already central; do not rebuild this sealed namespace'
        target=private/source.name
        if source.is_dir():
            if target.exists():assert target.is_junction() and target.resolve()==source.resolve()
            else:subprocess.run(['powershell.exe','-NoProfile','-Command','New-Item -ItemType Junction -Path '+quote(target)+' -Target '+quote(source)+' | Out-Null'],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            count+=1
        elif not target.exists():shutil.copy2(source,target)
        else:assert target.read_bytes()==source.read_bytes()
    namespace=private/'LiveRiding_v01';namespace.mkdir(exist_ok=True);assert not namespace.is_junction()
    proof={'passed':True,'approved_library_junctions':count,'private_namespace':str(namespace),'normal_content_modified':False}
    (workspace/'LiveRidingLab/content_layout.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');return proof
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve())))
