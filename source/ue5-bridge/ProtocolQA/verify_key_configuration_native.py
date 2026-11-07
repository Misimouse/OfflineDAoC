"""Exercise actual native controls page/capture and isolated settings, without starting a server."""
import argparse,json,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest
from verify_options_audio_native import read

def verify(workspace,engine,installed=False):
    root=workspace/'KeyConfigurationLab';build=read(root/'native_build.json')
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert build['passed']
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['key_configuration_installed'] and digest(normal)==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    else:assert digest(normal)==build['normal_binary_sha256']
    repo=Path(__file__).resolve().parents[3]
    source=repo/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    project=Path(build['project'])
    assert all(digest(project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64'/p)==h for p,h in build['binaries_sha256'].items())
    if installed:project=workspace/'Client/DAoCBridgeClient.uproject'
    output=root/('InstalledControlsAcceptance' if installed else 'Acceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    report=output/'controls.json';settings=output/'camera.json';keys=output/'keybindings.ini'
    settings.write_text(json.dumps({'mouse_sensitivity':.25,'invert_mouse':False,'preserved_test_field':'retained'}))
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly',
          '-DaocBridgeKeyConfigurationTest='+str(report),'-DaocBridgeControlsSettings='+str(settings),'-DaocBridgeKeyConfiguration='+str(keys),
          '-nosound','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(output/'engine.log')]
    with (output/'stdout.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=100,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0 and report.exists(),str(output)
    data=read(report);assert data['passed'] and not data['failures'] and data['checks']>=45,data
    assert digest(normal)==(build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256'])
    data.update(installed_client=installed,server_started=False,normal_installation_modified=False,build_receipt_sha256=digest(root/'native_build.json'),screenshot=str(report)+'.png')
    (output/'verified.json').write_text(json.dumps(data,indent=2))
    return dict(passed=True,checks=data['checks'],output=str(output))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--installed',action='store_true');a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.installed)))
