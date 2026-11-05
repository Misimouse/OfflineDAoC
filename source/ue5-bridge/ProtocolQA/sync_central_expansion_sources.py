"""Keep installed plugin sources equal to the sources used by the accepted private build."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sync(workspace, apply=False):
    lab = workspace/'ExpansionRaceLab'
    receipt_path = lab/'CentralDelivery/installed_client.json'
    receipt = json.loads(receipt_path.read_text())
    assert receipt['installed'] and receipt['client_only'] and not receipt['normal_database_modified']
    canonical = Path(__file__).resolve().parents[3]/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge/Source'
    compiled = lab/'StarterNativeBuild/HostProject/Plugins/DAoCVisualBridge/Source'
    target_root = workspace/'Client/Plugins/DAoCVisualBridge/Source'
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    changes = []
    for path in sorted(canonical.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(canonical)
        built = compiled/relative
        target = target_root/relative
        assert digest(path) == digest(built), ('Canonical source changed since accepted build', str(relative))
        assert target.resolve().is_relative_to(target_root.resolve()) and target.is_file()
        if digest(target) != digest(path):
            changes.append({'source': str(path), 'target': str(target),
                            'before_sha256': digest(target), 'after_sha256': digest(path)})
    if not apply:
        return {'passed': True, 'dry_run': True, 'source_files_to_sync': len(changes)}
    if not changes:
        return {'passed': True, 'source_files_synced': 0, 'already_current': True}
    backups = Path(receipt['backup_directory'])/'Sources'
    assert backups.resolve().is_relative_to((workspace/'Backups').resolve())
    backups.mkdir(exist_ok=True)
    changed = []
    try:
        for index, row in enumerate(changes):
            target = Path(row['target'])
            assert digest(target) == row['before_sha256']
            saved = backups/(str(index)+'_'+target.name)
            assert not saved.exists()
            shutil.copy2(target, saved)
            row['backup'] = str(saved)
        (backups/'rollback.json').write_text(json.dumps(changes, indent=2), encoding='utf-8')
        for row in changes:
            changed.append(row)
            shutil.copy2(row['source'], row['target'])
            assert digest(Path(row['target'])) == row['after_sha256']
        receipt['source_sync'] = {'passed': True, 'files': changes,
                                  'scope': 'Installed sources match the source payload used by the tested binary.'}
        receipt['installed_files'].update({row['target']: row['after_sha256'] for row in changes})
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    except BaseException:
        for row in reversed(changed):
            shutil.copy2(row['backup'], row['target'])
            assert digest(Path(row['target'])) == row['before_sha256']
        raise
    return {'passed': True, 'source_files_synced': len(changes), 'normal_database_modified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(sync(args.workspace.resolve(), args.apply)))
