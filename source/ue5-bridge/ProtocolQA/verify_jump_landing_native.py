"""Verify actual native jump and landing physics in a transient scene."""
import argparse,json,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest

def verify(workspace,engine,lab_name="JumpLandingLab"):
    assert lab_name in ["JumpLandingLab","LiveRidingLab","KeyConfigurationLab","InterfaceKeysLab","DisplaySettingsLab","DisplaySettingsFixLab","GuildWindowLab","EmblemWindowLab","ItemHandoverLab","HoverDetailsLab","UIScaleLab","WindowRecoveryLab","PlayerVitalsLab","CompassLab","WorldClockLab"]
    root=workspace/lab_name;build=json.loads((root/'native_build.json').read_text())
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert build['passed'] and digest(normal)==build['normal_binary_sha256']
    output=root/'PhysicsAcceptance'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    report=output/'physics.json'
    command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),build['project'],'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeJumpLandingTest='+str(report),'-nosound','-nullrhi','-unattended','-nosplash','-abslog='+str(output/'engine.log')]
    with (output/'stdout.log').open('w',encoding='utf-8') as log:p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=100,creationflags=subprocess.CREATE_NO_WINDOW)
    assert p.returncode==0 and report.exists(),str(output)
    raw=report.read_bytes();state=json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
    assert state['passed'] and state['checks']>=9 and not state['failures'],state
    assert digest(normal)==build['normal_binary_sha256']
    state.update(normal_installation_modified=False,server_started=False,build_receipt_sha256=digest(root/'native_build.json'))
    (output/'verified.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    return dict(passed=True,checks=state['checks'],jump_apex_cm=state['jump_apex_cm'],fall_impact_mps=state['fall_impact_mps'],output=str(output))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','engine']:parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve())))
