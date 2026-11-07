"""Preview/install the exact verified display settings successor, with backups."""
import argparse,json,shutil,socket
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files,DISPLAY_NATIVE_TARGETS,DISPLAY_NEW_NAMES
from prepare_combined_expansion_data import digest

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def latest(p):return sorted(p.glob('*/verified.json'))[-1]
def install(workspace,apply=False,rollback=False):
    lab_name='DisplaySettingsFixLab';root=workspace/lab_name;rp=workspace/'DisplaySettingsLab/installed.json';plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    if rp.exists() and read(rp).get('installed') and not rollback:
        verify_files(workspace);return dict(passed=True,already_current=True)
    verify_files(workspace)
    if rollback:
        receipt=read(rp);assert receipt['installed'] and receipt['phase']=='complete';rows=receipt['files']
    else:
        bp=root/'native_build.json';build=read(bp);assert build['passed'];prior=workspace/'InterfaceKeysLab/installed.json';previous=read(prior)
        assert previous['native_after_sha256']==build['normal_binary_sha256']
        specific_manifest=read(root/'display_acceptance.json');specific_path=Path(specific_manifest['proof']);assert digest(specific_path)==specific_manifest['proof_sha256'];specific=read(specific_path);assert specific['passed'] and specific['checks']>=47 and not specific['failures'] and specific['build_receipt_sha256']==digest(bp)
        reg_path=root/'regressions.json';reg=read(reg_path);assert reg['passed'] and reg['build_receipt_sha256']==digest(bp)
        evidence=[bp,specific_path,reg_path,root/'reference_audit.json']
        audit=read(evidence[-1]);assert audit['passed'] and all(digest(Path(p))==h for p,h in audit['input_hashes'].items())
        for name,n in [('controls',256),('movement',53),('jump',9),('tracking',35),('water',65550)]:
            case=reg['results'][name];assert case['passed'] and case['checks']>=n
            proof=Path(case['output'])/'verified.json';assert read(proof)['build_receipt_sha256']==digest(bp);evidence.append(proof)
        audio=Path(reg['results']['audio_ui']['report_directory'])/'verified.json';v=read(audio);assert v['passed'] and v['build_receipt_sha256']==digest(bp);evidence.append(audio)
        for name,n in [('server_sound',40),('footstep',149),('door',15),('options',17),('selection',15),('combat',14),('spell',15)]:assert v['reports'][name]['passed'] and v['reports'][name]['checks']>=n
        startup_path=latest(root/'StartupAcceptance');startup=read(startup_path);assert startup['passed'] and len(startup['reports'])==2 and startup['build_receipt_sha256']==digest(bp);evidence.append(startup_path)
        repo=Path(__file__).resolve().parents[3];source=repo/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge';candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge'
        assert all(digest(source/'Source'/p)==h for p,h in build['source_sha256'].items())
        prior_build=workspace/'InterfaceKeysLab/native_build.json';assert digest(prior_build)==previous['evidence'][str(prior_build)]
        before_sources={Path(p).as_posix():h for p,h in read(prior_build)['source_sha256'].items()};rows=[]
        for rel in DISPLAY_NATIVE_TARGETS:
            origin=(candidate if rel.startswith('Binaries/') else source)/rel;target=plugin/rel;assert target.resolve().is_relative_to(workspace.resolve())
            old=digest(target) if target.exists() else None;assert (old is None)==(target.name in DISPLAY_NEW_NAMES)
            if old is not None and rel.startswith('Source/'):assert old==before_sources[rel.removeprefix('Source/')]
            if rel.startswith('Binaries/'):assert digest(origin)==build['binaries_sha256'][target.name]
            rows.append(dict(source=str(origin),target=str(target),before_sha256=old,after_sha256=digest(origin)))
        receipt=dict(installed=False,phase='planned',database_modified=False,server_rules_modified=False,owner_gameplay_accepted=False,
          native_before_sha256=build['normal_binary_sha256'],native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],
          predecessor_receipt_sha256=digest(prior),files=rows,evidence={str(p):digest(p) for p in evidence})
        (root/'install_plan.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    if not apply:return dict(passed=True,dry_run=True,files=len(rows),rollback=rollback)
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        if rollback:
            for row in rows:
                assert Path(row['target']).resolve().is_relative_to(workspace.resolve()) and digest(Path(row['target']))==row['after_sha256']
                if row['before_sha256'] is not None:assert digest(Path(row['backup']))==row['before_sha256']
            for row in reversed(rows):
                if row['before_sha256'] is None:Path(row['target']).unlink()
                else:shutil.copy2(row['backup'],row['target'])
            receipt.update(installed=False,phase='rolled_back');rp.write_text(json.dumps(receipt,indent=2));verify_files(workspace);return dict(passed=True,rolled_back=True)
        backup=workspace/'Backups'/(lab_name+'_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        for i,row in enumerate(rows):
            target=Path(row['target']);assert (digest(target) if target.exists() else None)==row['before_sha256'] and digest(Path(row['source']))==row['after_sha256']
            if row['before_sha256'] is not None:
                saved=backup/str(i);shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        receipt.update(phase='backed_up',backup_directory=str(backup));rp.write_text(json.dumps(receipt,indent=2));changed=[]
        try:
            for row in rows:
                target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True);changed.append(row);shutil.copy2(row['source'],target);assert digest(target)==row['after_sha256']
            receipt.update(installed=True,phase='complete');rp.write_text(json.dumps(receipt,indent=2));verify_files(workspace);shutil.copy2(rp,root/'installed.json')
        except BaseException:
            for row in reversed(changed):
                target=Path(row['target']);assert target.resolve().is_relative_to(workspace.resolve())
                if row['before_sha256'] is None:target.unlink(missing_ok=True)
                else:assert digest(Path(row['backup']))==row['before_sha256'];shutil.copy2(row['backup'],target)
            receipt.update(installed=False,phase='rolled_back');rp.write_text(json.dumps(receipt,indent=2));raise
    return dict(passed=True,installed=True,files=len(rows),backup_directory=str(backup),database_modified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--rollback',action='store_true');a=p.parse_args();print(json.dumps(install(a.workspace.resolve(),a.apply,a.rollback)))
