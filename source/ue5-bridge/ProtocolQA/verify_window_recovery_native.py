"""Exercise original window recovery against a private offscreen viewport; no server."""
import argparse,json,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest
from verify_options_audio_native import read

def verify(workspace,engine,installed=False,lab_name="WindowRecoveryLab"):
    assert lab_name in ["WindowRecoveryLab","PlayerVitalsLab","CompassLab"]
    root=workspace/lab_name;bp=root/'native_build.json';build=read(bp);assert build['passed']
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';expected=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256']
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['window_recovery_installed']
    assert digest(normal)==expected
    out=root/('InstalledWindowAcceptance' if installed else 'WindowAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True);report=out/'windows.json'
    fixture=out/'fixture.json';fixture.write_bytes((workspace/'Reports/vault/fixture.json').read_bytes())
    interface=out/'interface.ini';interface.write_text('[Interface]\nVersion=1\nUIScale=1.0\n')
    keys=out/'keys.ini';keys.write_text('[Bindings]\nshow_inventory0=Ctrl+I\n');keys_before=keys.read_bytes();interface_before=interface.read_bytes()
    project=str(workspace/'Client/DAoCBridgeClient.uproject') if installed else build['project']
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),project,'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly',
      '-DaocBridgeWindowRecoveryTest='+str(report),'-DaocBridgeWindowFixture='+str(fixture),'-DaocBridgeInterfaceSettings='+str(interface),'-DaocBridgeEquipmentCatalog='+str(workspace/'equipment_catalog_v01.json'),'-DaocBridgeDisplaySettings='+str(out/'display.ini'),'-DaocBridgeKeyConfiguration='+str(out/'keys.ini'),
      '-DaocBridgeControlsSettings='+str(out/'camera.json'),'-DaocBridgeAudioSettings='+str(out/'audio.ini'),
      '-nosound','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(out/'engine.log')]
    if installed:args=[v for v in args if not v.startswith('-DaocBridgeEmblemUI=')]
    with (out/'stdout.log').open('w',encoding='utf-8') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=360,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0 and report.exists(),str(out)
    data=read(report);assert data['passed'] and not data['failures'] and data['checks']>=53,data
    assert digest(normal)==expected and keys.read_bytes()==keys_before and interface.read_bytes()==interface_before
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    data.update(build_receipt_sha256=digest(bp),normal_installation_modified=False,actual_slate_button_delegates=True);(out/'verified.json').write_text(json.dumps(data,indent=2))
    (root/('installed_window_acceptance.json' if installed else 'window_acceptance.json')).write_text(json.dumps(dict(passed=True,proof=str(out/'verified.json'),proof_sha256=digest(out/'verified.json')),indent=2))
    return dict(passed=True,checks=data['checks'],output=str(out))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);p.add_argument('--installed',action='store_true');a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.installed)))
