"""Reversibly install accepted additive client resources; never alter server data or activation."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def install(workspace, apply=False):
    workspace = workspace.resolve()
    delivery = workspace/'ExpansionRaceLab/CentralDelivery'
    manifest_path = delivery/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    proof_path = delivery/'NativeAcceptance/verified.json'
    proof = json.loads(proof_path.read_text())
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert manifest['passed'] and not manifest['installed'] and proof['passed']
    assert proof['material_isolation_passed'] and proof['partial_override_inherits_central_hair']
    assert proof['known_source_geometry_failure'] == ['world and frozen miniature publish actual facial render weights 1419']
    assert all(digest(Path(name)) == expected for name, expected in proof['inputs'].items())
    assert digest(Path(manifest['source_seal']['path'])) == manifest['source_seal']['sha256']
    receipt_path = delivery/'installed_client.json'
    if receipt_path.exists():
        previous = json.loads(receipt_path.read_text())
        assert previous['installed'] and previous['manifest_sha256'] == digest(manifest_path)
        assert all(digest(Path(name)) == sha for name, sha in previous['installed_files'].items())
        return previous
    replacement = []
    for name, row in manifest['catalogs'].items():
        source, target = Path(row['candidate']), Path(row['target'])
        assert source.resolve().is_relative_to(delivery) and target.resolve().is_relative_to(workspace)
        assert digest(source) == row['after_sha256'] and digest(target) == row['before_sha256']
        replacement.append((source, target, row['after_sha256']))
    private = workspace/'ExpansionRaceLab/CentralDeliveryHost/Plugins/DAoCVisualBridge/Binaries/Win64'
    central = workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64'
    for name in ['UnrealEditor-DAoCVisualBridge.dll', 'UnrealEditor.modules']:
        source, target = private/name, central/name
        assert target.is_file() and source.is_file()
        replacement.append((source, target, digest(source)))
    assert json.loads((private/'UnrealEditor.modules').read_text())['BuildId'] == json.loads((central/'UnrealEditor.modules').read_text())['BuildId']
    added = []
    content = workspace/'Client/Plugins/DAoCVisualBridge/Content'
    for row in manifest['assets']:
        source, target = Path(row['source']), Path(row['target'])
        assert source.resolve().is_relative_to(workspace.parent) and target.resolve().is_relative_to(content.resolve())
        assert digest(source) == row['sha256']
        if target.exists():
            assert digest(target) == row['sha256']
        else:
            added.append((source, target, row['sha256']))
    required = sum(source.stat().st_size for source, _, _ in added)
    assert shutil.disk_usage(workspace).free > required+512*1024*1024
    preview = {'passed': True, 'dry_run': True, 'assets_to_add': len(added), 'bytes_to_copy': required,
               'files_to_replace': len(replacement), 'normal_database_modified': False,
               'activation_changed': False, 'global_appearance_materials_preserved': True}
    (delivery/'client_install_dry_run.json').write_text(json.dumps(preview, indent=2), encoding='utf-8')
    if not apply:
        return preview
    # Do not replace a library loaded by an editor or a running client.
    check = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                            "@(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue).Count"],
                           capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert check.stdout.strip() == '0', 'Close UE editors/game normally before applying the accepted client delivery'
    backup = workspace/'Backups'/('CentralExpansionClient_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True)
    assert backup.resolve().is_relative_to(workspace/'Backups')
    backups = []
    for index, (_, target, _) in enumerate(replacement):
        saved = backup/(str(index)+'_'+target.name)
        shutil.copy2(target, saved)
        backups.append({'target': str(target), 'backup': str(saved), 'sha256': digest(saved)})
    rollback = {'existing_files': backups, 'new_files': [{'target': str(t), 'sha256': sha} for _, t, sha in added]}
    (backup/'rollback.json').write_text(json.dumps(rollback, indent=2), encoding='utf-8')
    copied = []
    changed = []
    try:
        for source, target, sha in added:
            assert not target.exists()
            target.parent.mkdir(parents=True, exist_ok=True)
            copied.append((target, sha))
            shutil.copy2(source, target)
            assert digest(target) == sha
        for index, (source, target, sha) in enumerate(replacement):
            changed.append(index)
            shutil.copy2(source, target)
            assert digest(target) == sha
        files = {str(target): sha for _, target, sha in replacement+added}
        result = {'installed': True, 'client_only': True, 'manifest_sha256': digest(manifest_path),
                  'native_acceptance_sha256': digest(proof_path), 'backup_directory': str(backup),
                  'installed_files': files, 'normal_database_modified': False,
                  'server_binaries_modified': False, 'activation_changed': False,
                  'global_appearance_materials_preserved': True}
        receipt_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
        return {k: v for k, v in result.items() if k != 'installed_files'}
    except BaseException:
        for index in reversed(changed):
            row = backups[index]
            shutil.copy2(row['backup'], row['target'])
            assert digest(Path(row['target'])) == row['sha256']
        for target, _ in reversed(copied):
            assert target.resolve().is_relative_to(content.resolve())
            target.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(install(args.workspace, args.apply)))
