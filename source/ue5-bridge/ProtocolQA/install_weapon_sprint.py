"""Install only verified weapon/sprint controls outputs, with exact hash guards and rollback."""
import argparse
from contextlib import ExitStack
from datetime import datetime
import json
from pathlib import Path
import shutil
import socket
from central_activation_receipts import verify_files
from weapon_sprint_receipts import read, expected_files
from prepare_combined_expansion_data import digest


def install(workspace, apply=False):
    root = workspace/'OriginalControlsLab'
    baseline = verify_files(workspace)
    if baseline['weapon_sprint_installed']:
        return dict(passed=True, already_current=True)
    assert baseline['npc_effects_installed']
    predecessor = workspace/'NpcEffectsLab/installed.json'
    proofs = read(root/'delivery_proofs.json')
    rows = expected_files(workspace, proofs)
    for row in rows:
        target = Path(row['target'])
        assert (digest(target) if target.exists() else None) == row['before_sha256'], str(target)
    evidence = [root/p for p in ['native_build.json','state_tests.json','gateway_tests.json','audit.json','delivery_proofs.json']]
    evidence += [Path(p) for p in proofs.values()]
    build = read(root/'native_build.json')
    receipt = dict(installed=False, phase='planned', database_modified=False,
                   server_rules_modified=False, map_geometry_modified=False, teleport_enabled=False,
                   owner_gameplay_accepted=False, proofs=proofs,
                   predecessor_receipt_sha256=digest(predecessor),
                   native_before_sha256=build['normal_binary_sha256'],
                   native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],
                   files=rows, evidence={str(p):digest(p) for p in evidence})
    plan, path = root/'install_plan.json', root/'installed.json'
    if not apply:
        plan.write_text(json.dumps(receipt, indent=2))
        return dict(passed=True, dry_run=True, files=len(rows))
    assert read(plan) == receipt
    simulation = read(root/'install_simulation.json')
    assert simulation['passed'] and simulation['simulated_only'] and simulation['plan_sha256'] == digest(plan)
    for name, sha in simulation['guard_sources'].items():
        assert digest(Path(__file__).with_name(name)) == sha
    with ExitStack() as stack:
        for kind, port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard = stack.enter_context(socket.socket(socket.AF_INET,kind))
            guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            guard.bind(('127.0.0.1',port))
            if kind == socket.SOCK_STREAM:
                guard.listen(1)
        backup = workspace/'Backups'/('WeaponSprint_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir()
        for index, row in enumerate(rows):
            origin, target = Path(row['source']), Path(row['target'])
            assert digest(origin) == row['after_sha256']
            assert (digest(target) if target.exists() else None) == row['before_sha256']
            if target.exists():
                saved = backup/str(index)
                shutil.copy2(target,saved)
                assert digest(saved) == row['before_sha256']
                row['backup'] = str(saved)
        receipt.update(phase='backed_up',backup_directory=str(backup))
        path.write_text(json.dumps(receipt,indent=2))
        changed = []
        try:
            for row in rows:
                origin, target = Path(row['source']), Path(row['target'])
                assert target.resolve().is_relative_to(workspace.resolve())
                target.parent.mkdir(parents=True,exist_ok=True)
                changed.append(row)
                shutil.copy2(origin,target)
                assert digest(target) == row['after_sha256']
            receipt.update(installed=True,phase='complete')
            path.write_text(json.dumps(receipt,indent=2))
            assert verify_files(workspace)['weapon_sprint_installed']
        except BaseException:
            for row in reversed(changed):
                target = Path(row['target'])
                assert target.resolve().is_relative_to(workspace.resolve())
                if row.get('backup'):
                    shutil.copy2(row['backup'],target)
                else:
                    target.unlink(missing_ok=True)
            receipt.update(installed=False,phase='rolled_back')
            path.write_text(json.dumps(receipt,indent=2))
            raise
    return dict(passed=True,installed=True,files=len(rows),backup_directory=str(backup),database_modified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    options = parser.parse_args()
    print(json.dumps(install(options.workspace.resolve(),options.apply)))
