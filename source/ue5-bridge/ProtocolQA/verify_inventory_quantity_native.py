"""Exercise the actual Choose Quantity panel and guarded command in a private viewport."""
import argparse,json,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,engine,installed=False):
    root=workspace/'InventoryQuantityLab';bp=root/'native_build.json';build=json.loads(bp.read_text())
    assert build['passed']
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    expected=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256']
    assert digest(normal)==expected
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['inventory_quantity_installed']
    resources=json.loads((root/'resources.json').read_text());assert resources['passed']
    assert all(digest(Path(row['target']))==row['sha256'] for row in resources['files'])
    out=root/('InstalledNativeAcceptance' if installed else 'NativeAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    report=out/'quantity.json'
    project=str(workspace/'Client/DAoCBridgeClient.uproject') if installed else build['project']
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),project,'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeQuantityTest='+str(report),'-DaocBridgeEquipmentCatalog='+str(workspace/'equipment_catalog_v01.json')]
    for key,name in [('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:args.append('-DaocBridge'+key+'='+str(out/name))
    args+=['-nosound','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(out/'engine.log')]
    with (out/'stdout.log').open('w',encoding='utf-8') as log:result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=360,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0 and report.exists(),str(out)
    data=json.loads(report.read_text(encoding='utf-8-sig'));assert data['passed'] and data['checks']>=19 and not data['server_started'],data
    assert digest(normal)==expected
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    data.update(build_receipt_sha256=digest(bp),normal_installation_modified=False,resources_sha256=digest(root/'resources.json'))
    proof=out/'verified.json';proof.write_text(json.dumps(data,indent=2),encoding='utf-8')
    (root/('installed_native_acceptance.json' if installed else 'native_acceptance.json')).write_text(json.dumps(dict(passed=True,proof=str(proof),proof_sha256=digest(proof)),indent=2),encoding='utf-8')
    return dict(passed=True,checks=data['checks'],output=str(out))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);p.add_argument('--installed',action='store_true');a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.installed)))
