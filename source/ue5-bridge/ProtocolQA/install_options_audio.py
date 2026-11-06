"""Deliver original Esc/options art and volume controls, with guarded file rollback."""
import argparse
from contextlib import ExitStack
from datetime import datetime
import json
from pathlib import Path
import shutil
import socket
from central_activation_receipts import verify_files, OPTIONS_TARGETS
from prepare_combined_expansion_data import digest


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))


def install(workspace,apply=False,rollback=False):
    root=workspace/'OptionsAudioLab';receipt_path=root/'installed.json';plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    if receipt_path.exists() and read(receipt_path).get('installed') and not rollback:
        verify_files(workspace);return {'passed':True,'installed':True,'already_current':True}
    if rollback:
        receipt=read(receipt_path);assert receipt['installed'] and receipt['phase']=='complete'
        verify_files(workspace)
        rows=receipt['files']
    else:
        verify_files(workspace)
        build=read(root/'native_build.json');resources=read(root/'resources.json')
        proofs=sorted((root/'Acceptance').glob('*/verified.json'));assert proofs
        proof_path=proofs[-1];proof=read(proof_path)
        assert proof['passed'] and not proof['server_started'] and not proof['normal_binary_modified'] and not proof['installed_client']
        assert proof['build_receipt_sha256']==digest(root/'native_build.json') and proof['art_receipt_sha256']==digest(root/'resources.json')
        for name,count in [('options',17),('selection',15),('combat',14),('spell',15)]:
            row=proof['reports'][name];assert row['passed'] and not row['failures'] and row['checks']>=count
        predecessor=workspace/'TargetSelectionLab/installed.json';previous=read(predecessor)
        assert previous['installed'] and previous['native_after_sha256']==build['normal_binary_sha256']==proof['normal_sha256']
        source_root=Path(__file__).resolve().parents[3]/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge/Source'
        assert all(digest(source_root/name)==sha for name,sha in build['source_sha256'].items())
        assert digest(Path(resources['source']))==digest(Path(resources['candidate']))==resources['sha256']
        candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge'
        rows=[];new_names={'Source/DAoCVisualBridge/Private/DAoCBridgeOptions.cpp','Source/DAoCVisualBridge/Private/DAoCBridgeOptionsAcceptance.cpp','Content/ClassicUI/options.png'}
        for name in OPTIONS_TARGETS:
            target=plugin/name;assert target.resolve().is_relative_to(plugin.resolve())
            before=digest(target) if target.exists() else None
            assert (before is None)==(name in new_names),'Refuse an unexpected existing or missing target'
            if name.startswith('Binaries/'):
                source=candidate/name;expected=build['binaries_sha256'][Path(name).name]
            elif name.startswith('Source/'):
                relative=Path(name).relative_to('Source');source=source_root/relative;expected=build['source_sha256'][str(relative)]
            else:source=Path(resources['candidate']);expected=resources['sha256']
            assert digest(source)==expected
            rows.append({'target':str(target),'source':str(source),'before_sha256':before,'after_sha256':expected})
        receipt={'installed':False,'phase':'planned','database_modified':False,'predecessor_receipt_sha256':digest(predecessor),
            'native_before_sha256':build['normal_binary_sha256'],'native_after_sha256':rows[0]['after_sha256'],
            'evidence':{str(proof_path):digest(proof_path),str(root/'native_build.json'):digest(root/'native_build.json'),str(root/'resources.json'):digest(root/'resources.json')},'files':rows}
        (root/'install_plan.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    if not apply:return {'passed':True,'dry_run':True,'rollback':rollback,'files':len(rows)}
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        if rollback:
            for row in rows:
                target=Path(row['target']);assert target.resolve().is_relative_to(plugin.resolve()) and digest(target)==row['after_sha256']
                if row['before_sha256'] is not None:assert digest(Path(row['backup']))==row['before_sha256']
            for row in reversed(rows):
                target=Path(row['target']);assert target.resolve().is_relative_to(plugin.resolve()) and digest(target)==row['after_sha256']
                if row['before_sha256'] is None:target.unlink()
                else:assert digest(Path(row['backup']))==row['before_sha256'];shutil.copy2(row['backup'],target)
            receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');verify_files(workspace)
            return {'passed':True,'rolled_back':True,'audio_preferences_preserved':True}
        backup=workspace/'Backups'/('OptionsAudio_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        for i,row in enumerate(rows):
            target=Path(row['target']);assert (digest(target) if target.exists() else None)==row['before_sha256']
            if row['before_sha256'] is not None:
                saved=backup/str(i);shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        receipt.update(phase='backed_up',backup_directory=str(backup));receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        changed=[]
        try:
            for row in rows:
                changed.append(row);shutil.copy2(row['source'],row['target']);assert digest(Path(row['target']))==row['after_sha256']
            receipt.update(installed=True,phase='complete');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');verify_files(workspace)
        except BaseException:
            for row in reversed(changed):
                target=Path(row['target']);current=digest(target) if target.exists() else None
                if current==row['before_sha256']:continue
                assert current==row['after_sha256']
                if row['before_sha256'] is None:target.unlink()
                else:shutil.copy2(row['backup'],target)
            receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');raise
    return {'passed':True,'installed':True,'files':len(rows),'database_modified':False,'backup_directory':str(backup)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--apply',action='store_true');parser.add_argument('--rollback',action='store_true');args=parser.parse_args()
    print(json.dumps(install(args.workspace.resolve(),args.apply,args.rollback)))
