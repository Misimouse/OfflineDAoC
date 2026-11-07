"""Install one verified inventory backend successor; no native or server replacement."""
import argparse,json,shutil,socket
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def install(workspace,apply=False,rollback=False):
    root=workspace/'WeaponPoisonLab';rp=root/'installed.json';prior=workspace/'ItemHandoverLab/installed.json'
    if rp.exists() and read(rp).get('installed') and not rollback:
        verify_files(workspace);return dict(passed=True,already_current=True)
    verify_files(workspace)
    if rollback:
        receipt=read(rp);assert receipt['installed'] and receipt['phase']=='complete'
    else:
        previous=read(prior);source=Path(__file__).resolve().parents[1]/'Godot/inventory_state.gd';target=workspace/'Godot/inventory_state.gd'
        before=next(r['after_sha256'] for r in previous['files'] if r['target']==str(target));assert digest(target)==before
        evidence=[]
        for folder,minimum in [('StateTest',27),('Compatibility',0)]:
            proof=sorted((root/folder).glob('*/verified.json'))[-1];v=read(proof);assert v['passed']
            assert all(digest(Path(p))==h for p,h in v['source_inputs'].items())
            if minimum:assert v['checks']>=minimum
            else:
                for name,count in [('inventory',35),('inventory_rejection',11),('handover',36),('gateway',9)]:assert v['reports'][name]['passed'] and v['reports'][name]['checks']>=count
            evidence.append(proof)
        for mode,minimum in [('',8),('class',3)]:
            proof=next(p for p in reversed(sorted(root.glob('RealProtocol/*/real_protocol.json'))) if read(p).get('passed') and read(p).get('denial_mode')==mode);v=read(proof)
            assert len(v['checks'])>=minimum and all(v['checks'].values()) and all(v[k] for k in ['normal_shutdown','database_restored','candidate_server_restored','normal_runtime_unchanged'])
            assert all(digest(Path(p))==h for p,h in v['source_inputs'].items())
            assert v['candidate_server_build_sha256']==digest(workspace/'GuildWindowLab/ServerCandidate/build_receipt.json');evidence.append(proof)
        guard=root/'receipt_guard_tests.json';g=read(guard);assert g['passed'] and g['synthetic_only'] and g['checks']>=139 and g['test_source_sha256']==digest(Path(__file__).parent/'test_audio_receipt_chain.py');evidence.append(guard)
        receipt=dict(installed=False,phase='planned',database_modified=False,server_rules_modified=False,owner_gameplay_accepted=False,
            predecessor_receipt_sha256=digest(prior),native_sha256=previous['native_after_sha256'],
            files=[dict(source=str(source),target=str(target),before_sha256=before,after_sha256=digest(source))],evidence={str(p):digest(p) for p in evidence})
        (root/'install_plan.json').write_text(json.dumps(receipt,indent=2))
    row=receipt['files'][0];target=Path(row['target']);assert target==workspace/'Godot/inventory_state.gd'
    if not apply:return dict(passed=True,dry_run=True,files=1,rollback=rollback)
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        if rollback:
            assert digest(target)==row['after_sha256'] and digest(Path(row['backup']))==row['before_sha256']
            shutil.copy2(row['backup'],target);receipt.update(installed=False,phase='rolled_back');rp.write_text(json.dumps(receipt,indent=2));verify_files(workspace)
            return dict(passed=True,rolled_back=True)
        assert digest(target)==row['before_sha256'] and digest(Path(row['source']))==row['after_sha256']
        backup=workspace/'Backups'/('WeaponPoisonLab_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        saved=backup/target.name;shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        receipt.update(phase='backed_up',backup_directory=str(backup));rp.write_text(json.dumps(receipt,indent=2))
        try:
            shutil.copy2(row['source'],target);receipt.update(installed=True,phase='complete');rp.write_text(json.dumps(receipt,indent=2));verify_files(workspace)
        except BaseException:
            shutil.copy2(saved,target);receipt.update(installed=False,phase='rolled_back');rp.write_text(json.dumps(receipt,indent=2));raise
    return dict(passed=True,installed=True,files=1,backup_directory=str(backup),database_modified=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--rollback',action='store_true');a=p.parse_args();print(json.dumps(install(a.workspace.resolve(),a.apply,a.rollback)))
