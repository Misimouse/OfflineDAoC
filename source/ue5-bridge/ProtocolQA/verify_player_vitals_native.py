"""Check native living/dead gates and original animation using a real low-HP snapshot."""
import argparse,json,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest
from verify_options_audio_native import read

def verify(workspace,engine,fixture,installed=False,lab_name="PlayerVitalsLab"):
    assert lab_name in ["PlayerVitalsLab","CompassLab"]
    root=workspace/lab_name;bp=root/'native_build.json';build=read(bp);assert build['passed']
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    expected=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256'];assert digest(normal)==expected
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['player_vitals_installed']
    real=read(fixture.parent/'real_protocol.json');assert real['passed'] and real['case']=='after' and real['normal_shutdown'] and real['database_restored']
    out=root/('InstalledVitalsAcceptance' if installed else 'VitalsAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True);report=out/'vitals.json'
    capture=out/'fixture.json';capture.write_bytes(fixture.read_bytes());catalog=workspace/'models.json'
    project=str(workspace/'Client/DAoCBridgeClient.uproject') if installed else build['project']
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),project,'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly',
      '-DaocBridgePlayerVitalsTest='+str(report),'-DaocBridgeVitalsFixture='+str(capture),'-DaocBridgeCatalog='+str(catalog),'-DaocBridgeEquipmentCatalog='+str(workspace/'equipment_catalog_v01.json')]
    for key,name in [('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:args.append('-DaocBridge'+key+'='+str(out/name))
    args+=['-nosound','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(out/'engine.log')]
    inputs={str(p):digest(p) for p in [fixture,fixture.parent/'real_protocol.json',catalog]}
    with (out/'stdout.log').open('w',encoding='utf-8') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=360,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0 and report.exists(),str(out)
    data=read(report);assert data['passed'] and not data['failures'] and data['checks']>=23,data
    assert digest(normal)==expected and all(digest(Path(p))==h for p,h in inputs.items())
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    data.update(build_receipt_sha256=digest(bp),source_inputs=inputs,normal_installation_modified=False)
    (out/'verified.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    return dict(passed=True,checks=data['checks'],output=str(out))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','engine','fixture']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--installed',action='store_true');a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.fixture.resolve(),a.installed)))
