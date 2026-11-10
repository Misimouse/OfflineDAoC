"""Stage original trade art privately without editing the installed content tree."""
import argparse,json,shutil,subprocess
from pathlib import Path
from prepare_combined_expansion_data import digest

def prepare(workspace,install):
    root=workspace/'PlayerTradeUILab';content=root/'Content';content.mkdir(parents=True,exist_ok=True)
    central=workspace/'Client/Plugins/DAoCVisualBridge/Content'
    for origin in central.iterdir():
        target=content/origin.name
        if origin.name=='ClassicUI':
            target.mkdir(exist_ok=True)
            for asset in origin.iterdir():
                dest=target/asset.name
                if asset.is_dir():
                    if not dest.exists():subprocess.run(['powershell.exe','-NoProfile','-Command',"New-Item -ItemType Junction -Path '"+str(dest).replace("'","''")+"' -Target '"+str(asset).replace("'","''")+"' | Out-Null"],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
                    assert dest.is_junction() and dest.resolve()==asset.resolve()
                else:shutil.copy2(asset,dest)
        elif origin.is_dir():
            if not target.exists():subprocess.run(['powershell.exe','-NoProfile','-Command',"New-Item -ItemType Junction -Path '"+str(target).replace("'","''")+"' -Target '"+str(origin).replace("'","''")+"' | Out-Null"],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            assert target.is_junction() and target.resolve()==origin.resolve()
        else:shutil.copy2(origin,target)
    art=install/'new-client/godot/content/ui/classic/x4plus/trade.png';target=content/'ClassicUI/trade.png';assert not (central/'ClassicUI/trade.png').exists();shutil.copy2(art,target)
    receipt=dict(passed=True,source_art=str(art),sha256=digest(art),candidate_art=str(target),normal_content_modified=False)
    (root/'content_verified.json').write_text(json.dumps(receipt,indent=2));return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve(),a.install.resolve())))
