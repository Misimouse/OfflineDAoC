"""Install the accepted visible-body selection candidate with guarded rollback."""
import argparse
from contextlib import ExitStack
from datetime import datetime
import json
from pathlib import Path
import shutil
import socket
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))


def install(workspace,apply=False):
    root=workspace/'TargetSelectionLab';receipt_path=root/'installed.json'
    if receipt_path.exists() and read(receipt_path).get('installed'):
        verify_files(workspace);return {'passed':True,'already_current':True}
    verify_files(workspace)
    build=read(root/'native_build.json');assert build['passed'] and not build['normal_binary_modified']
    proofs=sorted((root/'Acceptance').glob('*/verified.json'));assert proofs
    proof_path=proofs[-1];proof=read(proof_path)
    assert proof['passed'] and not proof['server_started'] and not proof['normal_binary_modified']
    assert proof['build_receipt_sha256']==digest(root/'native_build.json')
    for name,minimum in [('selection',15),('combat',14),('spell',15)]:
        report=proof['reports'][name];assert report['passed'] and not report['failures'] and report['checks']>=minimum
    repo=Path(__file__).resolve().parents[3]
    source_root=repo/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source_root/name)==sha for name,sha in build['source_sha256'].items())
    candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge'
    plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    mode_path=workspace/'WeaponModeAudioLab/installed.json';mode=read(mode_path)
    assert mode['installed'] and mode['phase']=='complete'
    binary='Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(plugin/binary)==mode['native_sha256']==build['normal_binary_sha256']==proof['normal_sha256']
    paths=[binary,'Binaries/Win64/UnrealEditor.modules',
        'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h',
        'Source/DAoCVisualBridge/Private/DAoCBridgeInteraction.cpp',
        'Source/DAoCVisualBridge/Private/DAoCBridgeInteractionAcceptance.cpp']
    rows=[]
    for name in paths:
        target=plugin/name;assert target.exists() and target.resolve().is_relative_to(plugin.resolve())
        source=candidate/name if name.startswith('Binaries/') else source_root/Path(name).relative_to('Source')
        expected=build['binaries_sha256'][Path(name).name] if name.startswith('Binaries/') else build['source_sha256'][str(Path(name).relative_to('Source'))]
        assert digest(source)==expected
        rows.append({'source':str(source),'target':str(target),'before_sha256':digest(target),'after_sha256':expected})
    receipt={'installed':False,'phase':'planned','database_modified':False,
        'predecessor_receipt_sha256':digest(mode_path),'native_before_sha256':mode['native_sha256'],
        'native_after_sha256':rows[0]['after_sha256'],'build_receipt_sha256':digest(root/'native_build.json'),
        'proof_sha256':digest(proof_path),'files':rows,'owner_click_acceptance':False}
    (root/'install_plan.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    if not apply:return {'passed':True,'dry_run':True,'files':len(rows)}
    with ExitStack() as stack:
        # Conservatively reserve normal session ports for this short transaction.
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        backup=workspace/'Backups'/('TargetSelection_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        for i,row in enumerate(rows):
            assert digest(Path(row['target']))==row['before_sha256']
            saved=backup/str(i);shutil.copy2(row['target'],saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        receipt.update(phase='backed_up',backup_directory=str(backup));receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        changed=[]
        try:
            for row in rows:
                changed.append(row);shutil.copy2(row['source'],row['target']);assert digest(Path(row['target']))==row['after_sha256']
            receipt.update(installed=True,phase='complete');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');verify_files(workspace)
        except BaseException:
            for row in reversed(changed):
                current=digest(Path(row['target']));assert current in [row['before_sha256'],row['after_sha256']]
                shutil.copy2(row['backup'],row['target']);assert digest(Path(row['target']))==row['before_sha256']
            receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');raise
    return {'passed':True,'installed':True,'files':len(rows),'database_modified':False,'backup_directory':str(backup)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();print(json.dumps(install(args.workspace.resolve(),args.apply)))
