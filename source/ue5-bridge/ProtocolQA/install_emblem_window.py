"""Install only the verified emblem window successor, with exact backups."""
import argparse,json,shutil,socket
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files,EMBLEM_NATIVE_TARGETS,EMBLEM_GODOT_TARGETS,EMBLEM_NEW_NAMES,EMBLEM_UI_TARGETS
from prepare_combined_expansion_data import digest

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def latest(p):return sorted(p.glob('*/verified.json'))[-1]

def install(workspace,apply=False,rollback=False):
    root=workspace/'EmblemWindowLab';rp=root/'installed.json';plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    if rp.exists() and read(rp).get('installed') and not rollback:
        verify_files(workspace);return dict(passed=True,already_current=True)
    verify_files(workspace)
    if rollback:
        receipt=read(rp);assert receipt['installed'] and receipt['phase']=='complete';rows=receipt['files']
    else:
        bp=root/'native_build.json';build=read(bp);prior=workspace/'GuildWindowLab/installed.json';previous=read(prior)
        assert build['passed'] and previous['native_after_sha256']==build['normal_binary_sha256']
        manifest=read(root/'emblem_acceptance.json');specific_path=Path(manifest['proof']);specific=read(specific_path)
        assert digest(specific_path)==manifest['proof_sha256'] and specific['passed'] and specific['checks']>=29 and specific['build_receipt_sha256']==digest(bp)
        reg_path=root/'regressions.json';reg=read(reg_path);assert reg['passed'] and reg['build_receipt_sha256']==digest(bp)
        evidence=[bp,specific_path,reg_path]
        guard_path=root/'receipt_guard_tests.json';guard=read(guard_path)
        assert guard['passed'] and guard['synthetic_only'] and guard['checks']>=115 and guard['test_source_sha256']==digest(Path(__file__).parent/'test_audio_receipt_chain.py');evidence.append(guard_path)
        for name,n in [('guild',33),('display',47),('controls',257),('movement',53),('jump',9),('tracking',35),('water',65550)]:
            case=reg['results'][name];proof=Path(case['output'])/'verified.json'
            assert case['passed'] and case['checks']>=n and read(proof)['build_receipt_sha256']==digest(bp);evidence.append(proof)
        proof=Path(reg['results']['audio_ui']['report_directory'])/'verified.json';audio=read(proof)
        assert audio['passed'] and audio['build_receipt_sha256']==digest(bp);evidence.append(proof)
        for name,n in [('server_sound',40),('footstep',149),('door',15),('options',17),('selection',15),('combat',14),('spell',15)]:assert audio['reports'][name]['passed'] and audio['reports'][name]['checks']>=n
        source=Path(__file__).resolve().parents[1];native=source/'UnrealPlugin/DAoCVisualBridge';candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge'
        assert all(digest(native/'Source'/p)==h for p,h in build['source_sha256'].items())
        for folder,minimum in [('StateTest',33),('GatewayTest',12)]:
            proof=latest(root/folder);v=read(proof);assert v['passed'] and v['checks']>=minimum
            assert all(digest(Path(p))==h for p,h in v['source_inputs'].items());evidence.append(proof)
        server_path=workspace/'GuildWindowLab/ServerCandidate/build_receipt.json';server=read(server_path);assert server['passed'];evidence.append(server_path)
        real_path=next(p for p in reversed(sorted(root.glob('RealProtocol/*/real_protocol.json'))) if read(p).get('passed') and not read(p).get('restricted_member'));real=read(real_path)
        assert real['passed'] and len(real['checks'])>=9 and all(real['checks'].values()) and real['normal_shutdown'] and real['database_restored'] and real['candidate_server_restored'] and real['normal_runtime_unchanged']
        assert real['candidate_server_build_sha256']==digest(server_path) and all(digest(Path(p))==h for p,h in real['source_inputs'].items());evidence.append(real_path)
        restricted_path=next(p for p in reversed(sorted(root.glob('RealProtocol/*/real_protocol.json'))) if read(p).get('passed') and read(p).get('restricted_member'));restricted=read(restricted_path)
        assert restricted['checks']['server_permission_denied'] and restricted['candidate_server_build_sha256']==digest(server_path) and restricted['database_restored'] and restricted['candidate_server_restored'] and restricted['normal_shutdown'] and restricted['normal_runtime_unchanged'];evidence.append(restricted_path)
        assert all(digest(Path(p))==h for p,h in restricted['source_inputs'].items())
        resources_path=root/'resources.json';resources=read(resources_path);assert resources['passed'] and len(resources['files'])==2
        assert all(digest(Path(p))==h for p,h in {**resources['files'],**resources['input_hashes']}.items());evidence.append(resources_path)
        rows=[]
        def add(origin,target,expected=None):
            assert target.resolve().is_relative_to(workspace.resolve())
            old=digest(target) if target.exists() else None
            assert (old is None)==(target.name in EMBLEM_NEW_NAMES)
            if expected is not None:assert old==expected
            rows.append(dict(source=str(origin),target=str(target),before_sha256=old,after_sha256=digest(origin)))
        before={Path(p).as_posix():h for p,h in read(workspace/'GuildWindowLab/native_build.json')['source_sha256'].items()}
        for rel in EMBLEM_NATIVE_TARGETS:
            origin=(candidate if rel.startswith('Binaries/') else native)/rel
            add(origin,plugin/rel,before.get(rel.removeprefix('Source/')) if rel.startswith('Source/') else build['normal_binary_sha256'] if rel.endswith('.dll') else None)
            if rel.startswith('Binaries/'):assert digest(origin)==build['binaries_sha256'][Path(rel).name]
        for name in EMBLEM_GODOT_TARGETS:add(source/'Godot'/name,workspace/'Godot'/name)
        for rel in EMBLEM_UI_TARGETS:
            origin=Path(resources['root'])/Path(rel).name
            assert str(origin) in resources['files'];add(origin,plugin/rel)
        receipt=dict(installed=False,phase='planned',database_modified=False,server_rules_modified=False,owner_gameplay_accepted=False,
          native_before_sha256=build['normal_binary_sha256'],native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],
          predecessor_receipt_sha256=digest(prior),files=rows,evidence={str(p):digest(p) for p in evidence})
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
        backup=workspace/'Backups'/('EmblemWindowLab_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
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
