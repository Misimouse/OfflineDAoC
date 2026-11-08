"""Replay candidate entity lifecycle snapshots through the installed native actor consumer."""
import argparse,copy,json,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest
from central_activation_receipts import verify_files

def verify(workspace,engine):
    assert verify_files(workspace)['world_clock_installed']
    root=workspace/'StealthLab/Native'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');root.mkdir(parents=True)
    source=next(p for p in reversed(sorted((workspace/'StealthLab/Compatibility').glob('*/verified.json'))) if json.loads(p.read_text()).get('passed'))
    receipt=json.loads(source.read_text());assert receipt['checks']>=703 and receipt['reports']['test_stealth_state']['checks']>=27
    entity=source.parent/'Reports/entities/godot_lifecycle.json';data=json.loads(entity.read_text());assert data['passed'] and data['cases']
    # Entity-only unit snapshots predate the authoritative posture gate. Supply a
    # verified living/standing status, rather than bypassing that production gate.
    real=next(p for p in reversed(sorted((workspace/'StealthLab/RealProtocol').glob('*/verified.json'))) if json.loads(p.read_text()).get('passed') and not json.loads(p.read_text()).get('bug_reproduced'))
    real_receipt=json.loads(real.read_text());assert len(real_receipt['checks'])>=14 and all(real_receipt['checks'].values())
    status_path=real.parent/'active_snapshot.json';status=json.loads(status_path.read_text())['player_status']
    assert status['ready'] and status['vitals']['alive'] and not status['vitals']['sitting'] and not status['posture_uncertain'] and not status['posture_pending']
    for case in data['cases']:
        local=[r for r in case['snapshot']['entities'] if r['id']=='player:local']
        if local:
            assert len(local)==1 and local[0]['state']=='idle' and local[0]['health']>0
            case['snapshot']['player_status']=copy.deepcopy(status)
    fixture=root/'fixture.json';fixture.write_text(json.dumps(data),encoding='utf-8');normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    inputs={str(p):digest(p) for p in [normal,source,entity,real,status_path,fixture]}
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(workspace/'Client/DAoCBridgeClient.uproject'),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeEntityTest='+str(fixture),'-DaocBridgeCatalog='+str(workspace/'models.json'),'-nullrhi','-unattended','-nosound','-nosplash','-abslog='+str(root/'engine.log')]
    with (root/'stdout.log').open('w',encoding='utf-8') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
    native=Path(str(fixture)+'.native.json');assert r.returncode==0 and native.exists(),str(root)
    result=json.loads(native.read_text(encoding='utf-8-sig'));assert result['passed'] and not result['failures'] and result['checks']>=100,result
    assert all(digest(Path(p))==h for p,h in inputs.items());verify_files(workspace)
    result.update(source_inputs=inputs,normal_runtime_modified=False,owner_gameplay_accepted=False)
    (root/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return dict(passed=True,checks=result['checks'],output=str(root))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['workspace','engine']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve())))
