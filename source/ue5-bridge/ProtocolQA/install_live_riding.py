"""Preview, install or roll back the verified bounded live-riding client package."""
import argparse,json,shutil,socket
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files,LIVE_RIDING_NATIVE_TARGETS,LIVE_RIDING_GODOT_TARGETS,LIVE_RIDING_NEW_NAMES
from prepare_combined_expansion_data import digest

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def unchanged(rows):assert all(digest(Path(p))==sha for p,sha in rows.items())
def latest(root):return sorted(root.glob('*/verified.json'))[-1]

def install(workspace,apply=False,rollback=False):
    root=workspace/'LiveRidingLab';receipt_path=root/'installed.json';plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    if receipt_path.exists() and read(receipt_path).get('installed') and not rollback:
        verify_files(workspace);return dict(passed=True,already_current=True)
    verify_files(workspace)
    if rollback:
        receipt=read(receipt_path);assert receipt['installed'] and receipt['phase']=='complete';rows=receipt['files']
    else:
        build_path=root/'native_build.json';build=read(build_path);resources_path=root/'resources.json';resources=read(resources_path)
        audio_path=root/'audio_resources.json';audio=read(audio_path);import_path=root/'asset_import.json';assets=read(import_path)
        evidence=[build_path,resources_path,audio_path,import_path,root/'travel_routes.json']
        assert all(r['passed'] for r in [build,resources,audio,assets]);unchanged(resources['input_hashes']);unchanged(audio['input_hashes']);unchanged(audio['files']);unchanged(assets['files'])
        assert resources['catalog_sha256']==digest(root/'riding.json') and audio['catalog_sha256']==digest(Path(audio['catalog'])) and assets['catalog_sha256']==digest(root/'models.json')
        for folder,minimum in [('StateTest',68),('GatewayTest',8),('TravelTests',29),('AssetAcceptance',64),('InventoryRegression',35)]:
            path=latest(root/folder);proof=read(path);assert proof['passed'] and proof['checks']>=minimum and not proof.get('failures')
            if 'source_inputs' in proof:unchanged(proof['source_inputs'])
            if folder=='AssetAcceptance':assert proof['build_receipt_sha256']==digest(build_path) and proof['riding_catalog_sha256']==digest(root/'riding.json')
            evidence.append(path)
        native_path=latest(root/'NativeAcceptance');native=read(native_path)
        assert native['passed'] and native['build_receipt_sha256']==digest(build_path) and not native['normal_binary_modified']
        for name,minimum in [('server_sound',40),('footstep',149),('door',15),('options',17),('selection',15),('combat',14),('spell',15)]:
            proof=native['reports'][name];assert proof['passed'] and proof['checks']>=minimum and not proof['failures']
        evidence.append(native_path)
        movement_path=root/'movement_regressions.json';movement=read(movement_path);assert movement['passed'] and movement['build_receipt_sha256']==digest(build_path)
        for name,minimum in [('movement',53),('jump',9),('tracking',35),('water',65550)]:
            case=movement['results'][name];assert case['passed'] and case['checks']>=minimum
            path=Path(case['output'])/'verified.json';proof=read(path);assert proof['passed'] and proof['build_receipt_sha256']==digest(build_path);evidence.append(path)
        evidence.append(movement_path)

        full=space=None
        for path in sorted((workspace/'Reports/live_riding_real_protocol').glob('*/verified.json')):
            proof=read(path)
            if not proof.get('passed') or proof.get('native_inputs',{}).get(str(build_path))!=digest(build_path):continue
            if proof['checks'].get('original_route_reaches_final_path_point'):full=(path,proof)
            if proof['checks'].get('actual_space_key_dismount_request_and_ack'):space=(path,proof)
        assert full and space,'Require complete real itinerary and actual Space input on current binary'
        for path,proof in [full,space]:
            assert proof['normal_shutdown'] and proof['database_restored'] and not proof['errors'] and proof['native_exit']==0
            unchanged(proof['source_inputs']);unchanged(proof['native_inputs'])
            for name in ['unsupported_route_no_charge_no_item_no_mount','original_ticket_buy_mount_ack_and_pose','actual_server_route_movement','original_gallop_pcm_consumed_during_real_route','actual_dismount_ack_and_grounded_collision','no_new_hoof_sounds_after_dismount']:assert proof['checks'][name]
            evidence.append(path)
        catalog=read(root/'models.json');assert '448' not in read(workspace/'models.json') and catalog.pop('448')==assets['models']['448'] and catalog==read(workspace/'models.json')
        predecessor=workspace/'TargetTrackingLab/installed.json';assert read(predecessor)['native_after_sha256']==build['normal_binary_sha256']
        repo=Path(__file__).resolve().parents[3];source=repo/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge';godot=repo/'source/ue5-bridge/Godot'
        unchanged({str(source/'Source'/p):sha for p,sha in build['source_sha256'].items()})
        candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge'
        pairs=[(candidate/p if p.startswith('Binaries/') else source/p,plugin/p) for p in LIVE_RIDING_NATIVE_TARGETS]
        pairs += [(godot/p,workspace/'Godot'/p) for p in LIVE_RIDING_GODOT_TARGETS]+[(root/'models.json',workspace/'models.json')]
        content=[];private=candidate/'Content/LiveRiding_v01'
        for origin in assets['files']:
            origin=Path(origin);assert origin.resolve().is_relative_to(private.resolve());content.append((origin,plugin/'Content/LiveRiding_v01'/origin.relative_to(private)))
        content += [(root/name,plugin/'Content/LiveRiding_v01'/name) for name in ['riding.json','travel_routes.json']]
        audio_root=Path(audio['catalog']).parent
        for origin in [Path(audio['catalog'])]+[Path(p) for p in audio['files']]:
            assert origin.resolve().is_relative_to(audio_root.resolve());content.append((origin,plugin/'Content/LiveRiding_v01/Audio'/origin.relative_to(audio_root)))
        pairs+=content;rows=[]
        for origin,target in pairs:
            assert target.resolve().is_relative_to(workspace.resolve());before=digest(target) if target.exists() else None
            new=target.name in LIVE_RIDING_NEW_NAMES or target.is_relative_to(plugin/'Content/LiveRiding_v01')
            assert (before is None)==new
            rows.append(dict(source=str(origin),target=str(target),before_sha256=before,after_sha256=digest(origin)))
        receipt=dict(installed=False,phase='planned',database_modified=False,server_rules_modified=False,bounded_live_riding=True,cross_zone_travel=False,owner_gameplay_accepted=False,
            native_before_sha256=build['normal_binary_sha256'],native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],
            predecessor_receipt_sha256=digest(predecessor),resources_receipt_sha256=digest(resources_path),content_targets=[str(t) for _,t in content],files=rows,evidence={str(p):digest(p) for p in evidence})
        (root/'install_plan.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    if not apply:return dict(passed=True,dry_run=True,files=len(rows),rollback=rollback)
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard=stack.enter_context(socket.socket(socket.AF_INET,kind));guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1);guard.bind(('127.0.0.1',port))
            if kind==socket.SOCK_STREAM:guard.listen(1)
        if rollback:
            for row in rows:
                target=Path(row['target']);assert target.resolve().is_relative_to(workspace.resolve()) and digest(target)==row['after_sha256']
                if row['before_sha256'] is not None:assert digest(Path(row['backup']))==row['before_sha256']
            for row in reversed(rows):
                if row['before_sha256'] is None:Path(row['target']).unlink()
                else:shutil.copy2(row['backup'],row['target'])
            receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');verify_files(workspace);return dict(passed=True,rolled_back=True)
        backup=workspace/'Backups'/('LiveRiding_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir()
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
                target=Path(row['target']);assert target.resolve().is_relative_to(workspace.resolve())
                if row['before_sha256'] is None:target.unlink(missing_ok=True)
                else:assert digest(Path(row['backup']))==row['before_sha256'];shutil.copy2(row['backup'],target)
            receipt.update(installed=False,phase='rolled_back');receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');raise
    return dict(passed=True,installed=True,files=len(rows),backup_directory=str(backup),database_modified=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--rollback',action='store_true');a=p.parse_args();print(json.dumps(install(a.workspace.resolve(),a.apply,a.rollback)))
