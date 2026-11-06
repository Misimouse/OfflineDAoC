"""Inspect original rider animations and stable-horse imported skeleton privately."""
import argparse,json,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,engine):
    root=workspace/'LiveRidingLab';bp=root/'native_build.json';build=json.loads(bp.read_text(encoding='utf-8-sig'))
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';before=digest(normal)
    assert before==build['normal_binary_sha256'] and build['passed']
    output=root/'AssetAcceptance'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True);report=output/'assets.json'
    command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),build['project'],'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeLiveRidingAssetTest='+str(report),'-DaocBridgeCatalog='+str(workspace/'models.json'),'-nosound','-nullrhi','-unattended','-nosplash','-abslog='+str(output/'engine.log')]
    with (output/'stdout.log').open('w',encoding='utf-8') as log:process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=100,creationflags=subprocess.CREATE_NO_WINDOW)
    assert process.returncode==0 and report.exists(),str(output)
    raw=report.read_bytes();state=json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
    state.update(normal_installation_modified=False,server_started=False,build_receipt_sha256=digest(bp),catalog_sha256=digest(workspace/'models.json'))
    assert digest(normal)==before
    (output/'verified.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=state['passed'],checks=state['checks'],failures=state['failures'],output=str(output))))
    assert state['passed'] and state['checks']>=31 and not state['failures']
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();verify(a.workspace.resolve(),a.engine.resolve())
