"""Exercise native display settings against a private offscreen viewport; no server."""
import argparse,json,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest
from verify_options_audio_native import read

def verify(workspace,engine,installed=False,lab_name="DisplaySettingsFixLab"):
    assert lab_name in ['DisplaySettingsFixLab','GuildWindowLab','EmblemWindowLab','ItemHandoverLab']
    root=workspace/lab_name;bp=root/'native_build.json';build=read(bp);assert build['passed']
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';expected=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256']
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['item_handover_installed' if lab_name=='ItemHandoverLab' else 'emblem_window_installed' if lab_name=='EmblemWindowLab' else 'guild_window_installed' if lab_name=='GuildWindowLab' else 'display_settings_installed']
    assert digest(normal)==expected
    out=root/('InstalledDisplayAcceptance' if installed else 'DisplayAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True);report=out/'display.json'
    project=str(workspace/'Client/DAoCBridgeClient.uproject') if installed else build['project']
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),project,'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly',
      '-DaocBridgeDisplaySettingsTest='+str(report),'-DaocBridgeDisplaySettings='+str(out/'display.ini'),'-DaocBridgeKeyConfiguration='+str(out/'keys.ini'),
      '-DaocBridgeControlsSettings='+str(out/'camera.json'),'-DaocBridgeAudioSettings='+str(out/'audio.ini'),
      '-nosound','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(out/'engine.log')]
    with (out/'stdout.log').open('w',encoding='utf-8') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0 and report.exists(),str(out)
    data=read(report);assert data['passed'] and not data['failures'] and data['checks']>=47,data
    assert digest(normal)==expected
    data.update(build_receipt_sha256=digest(bp),normal_installation_modified=False,screenshot=str(report)+'.png');(out/'verified.json').write_text(json.dumps(data,indent=2))
    (root/('installed_display_acceptance.json' if installed else 'display_acceptance.json')).write_text(json.dumps(dict(passed=True,proof=str(out/'verified.json'),proof_sha256=digest(out/'verified.json')),indent=2))
    return dict(passed=True,checks=data['checks'],output=str(out))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);p.add_argument('--installed',action='store_true');a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.installed)))
