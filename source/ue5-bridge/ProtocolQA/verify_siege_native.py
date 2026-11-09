"""Validate original siege controls, ammunition, authority and cleanup in UE."""
import argparse,json,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,engine,installed=False,lab_name="SiegeWindowLab"):
    assert lab_name in ["SiegeWindowLab","GroundTargetLab"]
    root=workspace/lab_name;bp=root/'native_build.json';build=json.loads(bp.read_text());assert build['passed']
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';expected=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256'];assert digest(normal)==expected
    resource_path=workspace/'RvRWindowsLab/resources.json';resources=json.loads(resource_path.read_text());assert resources['passed'] and not resources['world_map_modified']
    assert all(digest(Path(r['target']))==r['sha256'] for r in resources['files'])
    out=root/('InstalledSiegeAcceptance' if installed and lab_name=='GroundTargetLab' else 'SiegeAcceptance' if lab_name=='GroundTargetLab' else 'InstalledNativeAcceptance' if installed else 'NativeAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    fixture=out/'fixture.json';fixture.write_bytes((workspace/'Reports/vault/fixture.json').read_bytes());report=out/'siege.json'
    project=str(workspace/'Client/DAoCBridgeClient.uproject') if installed else build['project']
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),project,'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeSiegeTest='+str(report),'-DaocBridgeSiegeFixture='+str(fixture),'-DaocBridgeEquipmentCatalog='+str(workspace/'equipment_catalog_v01.json')]
    for key,name in [('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:args.append('-DaocBridge'+key+'='+str(out/name))
    args+=['-nosound','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(out/'engine.log')]
    with (out/'stdout.log').open('w',encoding='utf-8') as log:result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=360,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0 and report.exists(),str(out)
    data=json.loads(report.read_text(encoding='utf-8-sig'));assert data['passed'] and data['checks']>=26 and not data['server_started'],data
    assert digest(normal)==expected and all(digest(source/p)==h for p,h in build['source_sha256'].items())
    data.update(build_receipt_sha256=digest(bp),normal_installation_modified=False,resources_sha256=digest(resource_path))
    proof=out/'verified.json';proof.write_text(json.dumps(data,indent=2),encoding='utf-8');(root/('siege_acceptance.json' if lab_name=='GroundTargetLab' else 'installed_native_acceptance.json' if installed else 'native_acceptance.json')).write_text(json.dumps(dict(passed=True,proof=str(proof),proof_sha256=digest(proof)),indent=2),encoding='utf-8')
    return dict(passed=True,checks=data['checks'],output=str(out))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve())))
