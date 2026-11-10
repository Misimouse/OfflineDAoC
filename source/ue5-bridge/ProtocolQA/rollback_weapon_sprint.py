"""Preview or restore this exact weapon/sprint controls delivery; refuse files changed afterwards."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import shutil
import socket
from central_activation_receipts import verify_files
from weapon_sprint_receipts import read, verify
from prepare_combined_expansion_data import digest


def rollback(workspace, apply=False):
    receipt, rows = verify(workspace)
    assert receipt and receipt['installed']
    backup = Path(receipt['backup_directory']).resolve()
    assert backup.is_relative_to((workspace/'Backups').resolve())
    for row in rows.values():
        target = Path(row['target']).resolve()
        assert target.is_relative_to(workspace.resolve())
        assert digest(target) == row['after_sha256']
        if row['before_sha256'] is not None:
            saved = Path(row['backup']).resolve()
            assert saved.is_relative_to(backup) and digest(saved) == row['before_sha256']
        else:
            assert not row.get('backup')
    if not apply:
        return dict(passed=True,dry_run=True,files=len(rows))
    with ExitStack() as stack:
        for kind,port in [(socket.SOCK_STREAM,10300),(socket.SOCK_DGRAM,10400),(socket.SOCK_STREAM,19727)]:
            guard = stack.enter_context(socket.socket(socket.AF_INET,kind))
            guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            guard.bind(('127.0.0.1',port))
            if kind == socket.SOCK_STREAM:
                guard.listen(1)
        path = workspace/'OriginalControlsLab/installed.json'
        preserved = {row['target']:Path(row['target']).read_bytes() for row in rows.values()}
        changed = []
        try:
            for row in reversed(list(rows.values())):
                target = Path(row['target'])
                assert target.resolve().is_relative_to(workspace.resolve())
                assert digest(target) == row['after_sha256']
                changed.append(row)
                if row['before_sha256'] is None:
                    target.unlink()
                else:
                    shutil.copy2(row['backup'],target)
                assert (digest(target) if target.exists() else None) == row['before_sha256']
            restored = dict(receipt,installed=False,phase='owner_rollback')
            path.write_text(json.dumps(restored,indent=2))
            assert verify_files(workspace)['npc_effects_installed']
            assert not verify_files(workspace)['weapon_sprint_installed']
        except BaseException:
            for row in reversed(changed):
                target = Path(row['target'])
                assert target.resolve().is_relative_to(workspace.resolve())
                target.write_bytes(preserved[row['target']])
                assert digest(target) == row['after_sha256']
            path.write_text(json.dumps(receipt,indent=2))
            raise
    return dict(passed=True,restored_predecessor=True,files=len(rows))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args = parser.parse_args()
    print(json.dumps(rollback(args.workspace.resolve(),args.apply)))
