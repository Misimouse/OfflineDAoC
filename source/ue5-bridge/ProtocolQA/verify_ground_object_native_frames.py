"""Compare measured original world bounds with actual imported Unreal mesh vertices."""
import argparse,json,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest


def verify(workspace,engine):
    lab=workspace/'GroundObjectsLab'
    read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    build=read(lab/'native_build.json');proof=read(lab/'catalogue_verified.json')
    assert build['passed'] and proof['passed'] and not (lab/'installed.json').exists()
    catalog=lab/'world_catalog_candidate.json';assert digest(catalog)==proof['sha256']
    assert all(digest(Path(p))==h for p,h in proof['source_inputs'].items())
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(normal)==build['normal_binary_sha256']
    project=Path(build['project']);binary=project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64'
    assert all(digest(binary/p)==h for p,h in build['binaries_sha256'].items())
    output=lab/'NativeFrameAcceptance'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    report=output/'frames.json'
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly',
          '-DaocBridgeGroundObjectFramesTest='+str(report),'-DaocBridgeGroundObjectCatalog='+str(catalog),
          '-NullRHI','-nosound','-unattended','-nosplash','-abslog='+str(output/'engine.log')]
    with (output/'stdout.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0 and report.exists(),str(output)
    data=read(report);assert data['passed'] and not data['failures'] and data['assets']==918 and data['models']==1021,data
    assert digest(normal)==build['normal_binary_sha256']
    data.update(installed=False,server_started=False,normal_runtime_modified=False,catalogue_sha256=digest(catalog),build_receipt_sha256=digest(lab/'native_build.json'))
    (output/'verified.json').write_text(json.dumps(data,indent=2))
    return dict(passed=True,assets=data['assets'],models=data['models'],vertices=data['vertices'],max_bounds_error_cm=data['max_bounds_error_cm'],output=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve())))
