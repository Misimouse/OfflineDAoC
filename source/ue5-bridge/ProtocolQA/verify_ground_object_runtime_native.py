"""Exercise original ground bodies and explicit identity-pinned pickup requests."""
import argparse,json,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest


def verify(workspace,engine,render=False,installed=False):
    lab=workspace/'GroundObjectRuntimeLab'
    prepared=workspace/'GroundObjectsLab'
    read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    build=read(lab/'native_build.json');proof=read(prepared/'catalogue_verified.json')
    assert build['passed'] and proof['passed']
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['ground_objects_installed']
    else:assert not (lab/'installed.json').exists()
    catalog=prepared/'world_catalog_candidate.json';assert digest(catalog)==proof['sha256']
    assert all(digest(Path(p))==h for p,h in proof['source_inputs'].items())
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(normal)==(build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256'])
    project=Path(build['project']);binary=project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64'
    assert all(digest(binary/p)==h for p,h in build['binaries_sha256'].items())
    if installed:project=workspace/'Client/DAoCBridgeClient.uproject';catalog=workspace/'Client/Plugins/DAoCVisualBridge/Content/WorldObjects_v01/world_catalog.json'
    output=lab/(('InstalledRenderedAcceptance' if render else 'InstalledNativeAcceptance') if installed else ('RenderedAcceptance' if render else 'NativeAcceptance'))/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    report=output/'frames.json'
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly',
          '-DaocBridgeGroundObjects','-DaocBridgeGroundObjectRuntimeTest='+str(report),'-DaocBridgeGroundObjectCatalog='+str(catalog),'-DaocBridgeKeyConfiguration='+str(output/'keybindings.ini'),'-DaocBridgeControlsSettings='+str(output/'controls.json'),
          '-NullRHI','-nosound','-unattended','-nosplash','-abslog='+str(output/'engine.log')]
    if render:
        args.remove('-NullRHI');args.extend(['-DaocBridgeGroundObjectCapture='+str(output),'-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720'])
    with (output/'stdout.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0 and report.exists(),str(output)
    data=read(report);assert data['passed'] and not data['failures'] and (data.get('captures')==2 if render else data['checks']>=20),data
    if render:
        from verify_stealth_render_native import png_rgb
        for name in ['front.png','rear.png']:
            (w,h),pixels=png_rgb(output/name);assert (w,h)==(1280,720) and max(pixels)-min(pixels)>100
    assert digest(normal)==(build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256'])
    data.update(installed=installed,server_started=False,normal_runtime_modified=False,catalogue_sha256=digest(catalog),build_receipt_sha256=digest(lab/'native_build.json'))
    (output/'verified.json').write_text(json.dumps(data,indent=2))
    return dict(passed=True,checks=data.get('checks',0),captures=data.get('captures',0),output=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--render',action='store_true');p.add_argument('--installed',action='store_true');a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.render,a.installed)))
