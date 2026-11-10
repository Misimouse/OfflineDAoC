"""Private original turn math plus delivered movement/backward cadence regressions."""
import argparse,json,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest

def verify(workspace,engine,lab_name="KeyboardTurningLab",installed=False):
    assert lab_name=="KeyboardTurningLab"
    root=workspace/lab_name;build=json.loads((root/'native_build.json').read_text());resources=json.loads((workspace/'MovementKeysLab/resources.json').read_text())
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert build['passed'] and resources['passed']
    expected=build['binaries_sha256'][normal.name] if installed else build['normal_binary_sha256']
    assert digest(normal)==expected
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['keyboard_turning_installed']
    assert all(digest(Path(p))==sha for p,sha in resources['input_hashes'].items())
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    output=root/('InstalledMathAcceptance' if installed else 'MathAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    report=output/'controls.json'
    command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),(str(workspace/'Client/DAoCBridgeClient.uproject') if installed else build['project']),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeMovementKeysTest='+str(report),'-DaocBridgeKeyboardTurningTest','-DaocBridgeMovementKeysCatalog='+resources['catalog'],'-DaocBridgeCatalog='+str(workspace/'models.json'),'-nosound','-nullrhi','-unattended','-nosplash','-abslog='+str(output/'engine.log')]
    with (output/'stdout.log').open('w',encoding='utf-8') as log:p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=100,creationflags=subprocess.CREATE_NO_WINDOW)
    assert p.returncode==0 and report.exists(),str(output)
    raw=report.read_bytes();state=json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
    assert state['passed'] and state['checks']==108 and state['models']==13 and not state['failures'],state
    assert digest(normal)==expected
    state.update(normal_installation_modified=False,server_started=False,build_receipt_sha256=digest(root/'native_build.json'),resources_receipt_sha256=digest(workspace/'MovementKeysLab/resources.json'))
    (output/'verified.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    return dict(passed=True,checks=state['checks'],models=13,output=str(output))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve())))
