"""Install the verified stealth successor, with exact predecessor guards and rollback."""
import argparse,json,shutil,socket,hashlib
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files,STEALTH_NATIVE_TARGETS,STEALTH_GODOT_TARGETS,STEALTH_NEW_NAMES
from prepare_combined_expansion_data import digest

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def latest(folder,minimum=0):
    for p in reversed(sorted(folder.glob('*/verified.json'))):
        d=read(p);checks=d.get('checks',0)
        if d.get('passed') and (len(checks) if isinstance(checks,dict) else checks)>=minimum:return p,d
    raise AssertionError('Verified evidence missing: '+str(folder))

def install(workspace,apply=False,rollback=False):
    root=workspace/'StealthLab';receipt_path=root/'installed.json';plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    current=verify_files(workspace)
    if current['stealth_installed'] and not rollback:return dict(passed=True,already_current=True)
    if rollback:
        receipt=read(receipt_path);assert receipt['installed'] and receipt['phase']=='complete';rows=receipt['files']
    else:
        assert current['world_clock_installed'] and not current['stealth_installed']
        predecessor=workspace/'WorldClockLab/installed.json';old_receipt=read(predecessor)
        bp=root/'native_build.json';build=read(bp);assert build['passed'] and build['normal_binary_sha256']==old_receipt['native_after_sha256']
        evidence=[bp];reg_path=root/'regressions.json';reg=read(reg_path)
        assert reg['passed'] and len(reg['results'])==16 and reg['build_receipt_sha256']==digest(bp);evidence.append(reg_path)
        for name,case in reg['results'].items():
            proof=Path(case['output'] if 'output' in case else case['report_directory'])/'verified.json';data=read(proof)
            assert case['passed'] and data['passed'] and data['build_receipt_sha256']==digest(bp);evidence.append(proof)
        state_path,state=latest(root/'Compatibility',719)
        assert state['passed'] and all(digest(Path(p))==h for p,h in state['source_inputs'].items());evidence.append(state_path)
        real_path,real=latest(root/'RealProtocol',18)
        assert real['normal_runtime_unchanged'] and real['database_restored'] and real['normal_shutdown'] and all(real['checks'].values());evidence.append(real_path)
        material_path,material=latest(root/'MaterialAcceptance',927)
        assert material['prepared_materials']>=2974 and material['normal_installation_modified']==False;evidence.append(material_path)
        visual_path,visual=latest(root/'RenderedAcceptance',14)
        assert visual['rendered'] and visual['pixel_checks']==3 and visual['pixel_measurements']['restoration_mean_error']<1;evidence.append(visual_path)
        for proof in [material,visual]:assert all(digest(Path(p))==h for p,h in proof['source_inputs'].items())
        guards_path=root/'receipt_guard_tests.json';guards=read(guards_path)
        assert guards['passed'] and guards['synthetic_only'] and guards['checks']>=58 and guards['test_source_sha256']==digest(Path(__file__).with_name('test_stealth_receipt_chain.py'));evidence.append(guards_path)
        source=Path(__file__).resolve().parents[1];native=source/'UnrealPlugin/DAoCVisualBridge';candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge'
        assert all(digest(native/'Source'/p)==h for p,h in build['source_sha256'].items())
        previous_build_path=workspace/'WorldClockLab/native_build.json';assert old_receipt['evidence'][str(previous_build_path)]==digest(previous_build_path)
        old_build=read(previous_build_path);old_sources={Path(p).as_posix():h for p,h in old_build['source_sha256'].items()}
        before_path=Path(old_receipt['godot_before_proof']);assert old_receipt['evidence'][str(before_path)]==digest(before_path)
        before=read(before_path);prior_rows={r['target']:r for r in old_receipt['files']};rows=[]
        def add(origin,target,expected):
            assert target.resolve().is_relative_to(workspace.resolve())
            actual=digest(target) if target.exists() else None;assert actual==expected,(str(target),'unexpected predecessor')
            rows.append(dict(source=str(origin),target=str(target),before_sha256=actual,after_sha256=digest(origin)))
        for rel in STEALTH_NATIVE_TARGETS:
            origin=(candidate if rel.startswith('Binaries/') else native)/rel;target=plugin/rel
            expected=None if target.name in STEALTH_NEW_NAMES else old_sources[rel.removeprefix('Source/')] if rel.startswith('Source/') else old_build['binaries_sha256'][target.name]
            add(origin,target,expected)
        for name in STEALTH_GODOT_TARGETS:
            origin=source/'Godot'/name;target=workspace/'Godot'/name;prior=prior_rows.get(str(target))
            expected=None if name in STEALTH_NEW_NAMES else prior['after_sha256'] if prior else before['source_inputs'][str(target)]
            assert digest(origin)==real['source_inputs'][str(origin)]
            add(origin,target,expected)
        runtime=root/'Runtime/stealth_materials.json';definition=read(runtime)
        assert definition['passed'] and definition['originals_unchanged'] and not definition.get('diagnostic_only') and len(definition['materials'])>=2974
        material_assets={}
        for asset in definition['materials'].values():
            assert asset.startswith(definition['library']+'/') and asset.startswith('/DAoCVisualBridge/Stealth_v01/') and '..' not in asset
            path=plugin/'Content'/(asset.split('.')[0].removeprefix('/DAoCVisualBridge/')+'.uasset')
            assert material['source_inputs'][str(path)]==digest(path);material_assets[str(path)]=digest(path)
        add(runtime,plugin/'Content/ClassicUI/stealth_materials.json',None);evidence.append(runtime)
        simulation_path=root/'install_simulation.json';simulation=read(simulation_path)
        assert simulation['passed'] and simulation['simulated_only'] and not simulation['normal_runtime_modified']
        assert simulation['targets_sha256']==hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
        assert simulation['test_source_sha256']==digest(Path(__file__).with_name('verify_stealth_install_simulation.py'))
        assert simulation['core_source_sha256']==digest(Path(__file__).with_name('central_activation_receipts.py'));evidence.append(simulation_path)
        receipt=dict(installed=False,phase='planned',database_modified=False,server_rules_modified=False,owner_gameplay_accepted=False,
                     predecessor_receipt_sha256=digest(predecessor),native_before_sha256=build['normal_binary_sha256'],native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],
                     godot_after_proof=str(real_path),material_proof=str(material_path),material_assets=material_assets,
                     files=rows,evidence={str(p):digest(p) for p in evidence})
        (root/'install_plan.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
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
            receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');verify_files(workspace)
            return dict(passed=True,rolled_back=True)
        backup=workspace/'Backups'/('StealthLab_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
        for i,row in enumerate(rows):
            target=Path(row['target']);assert (digest(target) if target.exists() else None)==row['before_sha256'] and digest(Path(row['source']))==row['after_sha256']
            if row['before_sha256'] is not None:
                saved=backup/str(i);shutil.copy2(target,saved);assert digest(saved)==row['before_sha256'];row['backup']=str(saved)
        receipt.update(phase='backed_up',backup_directory=str(backup));receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');changed=[]
        try:
            for row in rows:
                target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True);changed.append(row);shutil.copy2(row['source'],target);assert digest(target)==row['after_sha256']
            receipt.update(installed=True,phase='complete');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');verify_files(workspace)
        except BaseException:
            for row in reversed(changed):
                target=Path(row['target'])
                if row['before_sha256'] is None:target.unlink(missing_ok=True)
                else:assert digest(Path(row['backup']))==row['before_sha256'];shutil.copy2(row['backup'],target)
            receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');raise
    return dict(passed=True,installed=True,files=len(rows),backup_directory=str(backup),database_modified=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--rollback',action='store_true');a=p.parse_args();print(json.dumps(install(a.workspace.resolve(),a.apply,a.rollback)))
