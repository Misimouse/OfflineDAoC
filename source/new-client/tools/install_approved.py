"""Install the approved art snapshot. Preview by default; never edit stock content."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import shutil
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'approved/connacht-20261026'
MARKER = Path('enhanced/approved_assets.json')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def destination(project, name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not name.startswith('.enhanced-session/'):
        raise ValueError('Unsafe package destination: ' + name)
    target = project.joinpath(*path.parts)
    if not target.resolve().is_relative_to(project.resolve()):
        raise ValueError('Destination escapes project')
    return target

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT / 'godot')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--verify', action='store_true')
    mode.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    project = args.project.resolve()
    manifest = json.loads((PACKAGE / 'manifest.json').read_text(encoding='utf-8'))
    marker = project / MARKER
    receipt_path = project / '.enhanced-session/approved-install/receipt.json'
    if args.rollback:
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        for row in receipt['created']:
            target = destination(project, row['path'])
            if target.exists() and digest(target.read_bytes()) != row['sha256']:
                raise SystemExit('Rollback refused: file changed: ' + row['path'])
        if marker.exists() and digest(marker.read_bytes()) != receipt['marker_sha256']:
            raise SystemExit('Rollback refused: activation changed')
        marker.unlink(missing_ok=True)
        for row in receipt['created']:
            destination(project, row['path']).unlink(missing_ok=True)
        receipt_path.unlink()
        print('Approved art removed; pre-existing files and stock content preserved.')
        return
    for row in manifest['files']:
        destination(project, row['path'])
    if args.verify:
        for row in manifest['files']:
            target = destination(project, row['path'])
            if not target.is_file() or digest(target.read_bytes()) != row['sha256']:
                raise SystemExit('Verification failed: ' + row['path'])
        if not marker.is_file():
            raise SystemExit('Activation marker missing')
        print('Approved art verified:', len(manifest['files']), 'files')
        return
    print('Approved Connacht art:', len(manifest['files']), 'files,',
          round(sum(r['size'] for r in manifest['files']) / 1048576), 'MiB unpacked')
    if not args.apply:
        print('Preview only. Use --apply to install, --verify to check, --rollback to remove.')
        return
    if not (project / 'project.godot').is_file():
        raise SystemExit('Godot project missing')
    for zone in (207, 209):
        if not (project / f'content/zones/zone{zone}/zone.json').is_file():
            raise SystemExit('Supply converted v0.37c content first (zones 207 and 209).')
    # Preflight every collision before making any change. In particular, do not replace a live LAB.
    for row in manifest['files']:
        target = destination(project, row['path'])
        if target.exists() and digest(target.read_bytes()) != row['sha256']:
            raise SystemExit('Existing local profile differs; use a clean checkout: ' + row['path'])
    created = []
    old_marker = marker.read_bytes() if marker.exists() else None
    old_receipt = receipt_path.read_bytes() if receipt_path.exists() else None
    previous = json.loads(old_receipt)['created'] if old_receipt else []
    with tempfile.TemporaryDirectory(prefix='approved-art-') as staging:
        staged = Path(staging)
        for row in manifest['files']:
            # A matching existing file already passed the full hash preflight above.
            if destination(project, row['path']).exists():
                continue
            packed = b''.join((PACKAGE / 'blobs' / part).read_bytes() for part in row['parts'])
            data = zlib.decompress(packed)
            if len(data) != row['size'] or digest(data) != row['sha256']:
                raise SystemExit('Corrupt package: ' + row['path'])
            temp = staged / row['path']
            temp.parent.mkdir(parents=True, exist_ok=True)
            temp.write_bytes(data)
        try:
            for row in manifest['files']:
                target = destination(project, row['path'])
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(staged / row['path'], target)
                    created.append(row)
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(json.dumps({'schema': 1, 'package': manifest['id'],
                                         'enabled': True}) + '\n', encoding='utf-8')
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_text(json.dumps({'created': previous + created,
                'marker_sha256': digest(marker.read_bytes())}, indent=2), encoding='utf-8')
        except BaseException:
            for row in reversed(created):
                destination(project, row['path']).unlink(missing_ok=True)
            if old_marker is None: marker.unlink(missing_ok=True)
            else: marker.write_bytes(old_marker)
            if old_receipt is None: receipt_path.unlink(missing_ok=True)
            else: receipt_path.write_bytes(old_receipt)
            raise
    print('Approved art installed. Stock content, accounts and saves unchanged.')

if __name__ == '__main__':
    main()
