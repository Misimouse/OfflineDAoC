"""Install only verified positive-health life state, with exact backups."""
import argparse,json,shutil,socket
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files,PLAYER_VITALS_NATIVE_TARGETS,PLAYER_VITALS_NEW_NAMES,PLAYER_VITALS_GODOT_TARGETS
from prepare_combined_expansion_data import digest

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def latest(p):return sorted(p.glob('*/verified.json'))[-1]

def install(workspace,apply=False,rollback=False):
    root=workspace/'PlayerVitalsLab';rp=root/'installed.json';plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    if rp.exists() and read(rp).get('installed') and not rollback:
        verify_files(workspace);return dict(passed=True,already_current=True)
    verify_files(workspace)
    if rollback:
        receipt=read(rp);assert receipt['installed'] and receipt['phase']=='complete';rows=receipt['files']
    else:
        bp=root/'native_build.json';build=read(bp);prior=workspace/'WindowRecoveryLab/installed.json';previous=read(prior)
        assert build['passed'] and previous['native_after_sha256']==build['normal_binary_sha256']
        specific_path=latest(root/'VitalsAcceptance');specific=read(specific_path)
        assert specific['passed'] and specific['checks']>=23 and specific['build_receipt_sha256']==digest(bp)
        reg_path=root/'regressions.json';reg=read(reg_path);assert reg['passed'] and reg['build_receipt_sha256']==digest(bp)
        evidence=[bp,specific_path,reg_path]
        guard_path=root/'receipt_guard_tests.json';guard=read(guard_path)
        assert guard['passed'] and guard['synthetic_only'] and guard['checks']>=255 and guard['test_source_sha256']==digest(Path(__file__).parent/'test_audio_receipt_chain.py');evidence.append(guard_path)
        for name,n in [('windows',53),('scale',436),('hover',19),('handover',19),('emblem',29),('guild',33),('display',47),('controls',257),('movement',53),('jump',9),('tracking',35),('water',65550)]:
            case=reg['results'][name];proof=Path(case['output'])/'verified.json'
            assert case['passed'] and case['checks']>=n and read(proof)['build_receipt_sha256']==digest(bp);evidence.append(proof)
        proof=Path(reg['results']['audio_ui']['report_directory'])/'verified.json';audio=read(proof)
        assert audio['passed'] and audio['build_receipt_sha256']==digest(bp);evidence.append(proof)
        for name,n in [('server_sound',40),('footstep',149),('door',15),('options',17),('selection',15),('combat',14),('spell',15)]:assert audio['reports'][name]['passed'] and audio['reports'][name]['checks']>=n
        state_path=latest(root/'StateTest');state=read(state_path);assert state['passed'] and state['checks']>=32
        compatibility_path=latest(root/'Compatibility');compatibility=read(compatibility_path);assert compatibility['passed'] and compatibility['checks']>=413 and len(compatibility['reports'])==18
        real_path=sorted((root/'RealProtocol').glob('*/real_protocol.json'))[-1];real=read(real_path)
        assert real['passed'] and real['case']=='after' and real['real_protocol'] and real['disposable_only'] and real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged'] and len(real['checks'])>=10
        assert all(real['checks'].values())
        for report in [state,compatibility,real]:assert all(digest(Path(p))==h for p,h in report['source_inputs'].items())
        before_path=next(p for p in sorted((root/'BeforeProtocol').glob('*/real_protocol.json')) if read(p)['passed'])
        before_data=read(before_path);assert before_data['bug_reproduced'] and before_data['normal_runtime_unchanged']
        evidence.extend([state_path,compatibility_path,real_path,before_path])
        source=Path(__file__).resolve().parents[1];native=source/'UnrealPlugin/DAoCVisualBridge';candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge'
        assert all(digest(native/'Source'/p)==h for p,h in build['source_sha256'].items())
        old_build_path=workspace/'WindowRecoveryLab/native_build.json';hover=read(workspace/'WindowRecoveryLab/installed.json')
        assert str(old_build_path) in hover['evidence'] and digest(old_build_path)==hover['evidence'][str(old_build_path)]
        old_build=read(old_build_path);before={Path(p).as_posix():h for p,h in old_build['source_sha256'].items()};rows=[]
        for rel in PLAYER_VITALS_NATIVE_TARGETS:
            origin=(candidate if rel.startswith('Binaries/') else native)/rel;target=plugin/rel
            assert target.resolve().is_relative_to(workspace.resolve())
            old=digest(target) if target.exists() else None
            expected=None if target.name in PLAYER_VITALS_NEW_NAMES else before[rel.removeprefix('Source/')] if rel.startswith('Source/') else old_build['binaries_sha256'][target.name]
            assert old==expected
            if rel.startswith('Binaries/'):assert digest(origin)==build['binaries_sha256'][target.name]
            rows.append(dict(source=str(origin),target=str(target),before_sha256=old,after_sha256=digest(origin)))
        for name in PLAYER_VITALS_GODOT_TARGETS:
            origin=source/'Godot'/name;target=workspace/'Godot'/name;old=digest(target)
            assert old==before_data['source_inputs'][str(target)]
            rows.append(dict(source=str(origin),target=str(target),before_sha256=old,after_sha256=digest(origin)))
        receipt=dict(installed=False,phase='planned',database_modified=False,server_rules_modified=False,owner_gameplay_accepted=False,
          native_before_sha256=build['normal_binary_sha256'],native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],
          predecessor_receipt_sha256=digest(prior),godot_before_proof=str(before_path),files=rows,evidence={str(p):digest(p) for p in evidence})
        (root/'install_plan.json').write_text(json.dumps(receipt,indent=2))
    if not apply:return dict(passed=True,dry_run=True,files=len(rows),rollback=rollback)
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        if rollback:
            for row in rows:
                assert digest(Path(row['target']))==row['after_sha256']
                if row['before_sha256'] is not None:assert digest(Path(row['backup']))==row['before_sha256']
            for row in reversed(rows):
                if row['before_sha256'] is None:Path(row['target']).unlink()
                else:shutil.copy2(row['backup'],row['target'])
            receipt.update(installed=False,phase='rolled_back');rp.write_text(json.dumps(receipt,indent=2));verify_files(workspace);return dict(passed=True,rolled_back=True)
        backup=workspace/'Backups'/('PlayerVitalsLab_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        for i,row in enumerate(rows):
            target=Path(row['target']);assert (digest(target) if target.exists() else None)==row['before_sha256'] and digest(Path(row['source']))==row['after_sha256']
            if row['before_sha256'] is not None:
                saved=backup/str(i);shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        receipt.update(phase='backed_up',backup_directory=str(backup));rp.write_text(json.dumps(receipt,indent=2));changed=[]
        try:
            for row in rows:
                target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True);changed.append(row);shutil.copy2(row['source'],target);assert digest(target)==row['after_sha256']
            receipt.update(installed=True,phase='complete');rp.write_text(json.dumps(receipt,indent=2));verify_files(workspace)
        except BaseException:
            for row in reversed(changed):
                target=Path(row['target'])
                if row['before_sha256'] is None:target.unlink(missing_ok=True)
                else:assert digest(Path(row['backup']))==row['before_sha256'];shutil.copy2(row['backup'],target)
            receipt.update(installed=False,phase='rolled_back');rp.write_text(json.dumps(receipt,indent=2));raise
    return dict(passed=True,installed=True,files=len(rows),backup_directory=str(backup),database_modified=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--rollback',action='store_true');a=p.parse_args();print(json.dumps(install(a.workspace.resolve(),a.apply,a.rollback)))
