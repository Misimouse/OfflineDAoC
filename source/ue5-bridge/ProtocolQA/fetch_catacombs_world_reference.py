"""Fetch pinned public world tables, retaining only compressed verified copies."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import re
import urllib.request

COMMIT = 'b5b29c2ada7695414b94f5fa110eb505a477d007'


def fetch(workspace):
    root = workspace.resolve()/'References'/('DOLPublic_'+COMMIT[:12])
    manifest = json.loads((root/'catacombs_audit_manifest.json').read_text())
    assert manifest['repository'] == 'Dawn-of-Light/db-public' and manifest['commit'] == COMMIT
    tables = [row for row in manifest['tables'] if re.fullmatch(r'(Mob\.\d+|NpcTemplate|NPCEquipment)\.json', row['name'])]
    assert len(tables) == 7

    def one(row):
        path = root/(row['name']+'.gz')
        header = b'blob '+str(row['bytes']).encode()+b'\0'
        if path.exists():
            hash = hashlib.sha1(header)
            count = 0
            with gzip.open(path, 'rb') as source:
                for chunk in iter(lambda: source.read(1024*1024), b''):
                    count += len(chunk)
                    hash.update(chunk)
            assert count == row['bytes'] and hash.hexdigest() == row['git_blob']
            return {'name': row['name'], 'verified': True, 'cached': True}
        url = 'https://raw.githubusercontent.com/Dawn-of-Light/db-public/'+COMMIT+'/src/data/'+row['name']
        assert row['download_url'] == url
        pending = root/(row['name']+'.pending.gz')
        assert pending.resolve().is_relative_to(root.resolve()) and not pending.exists()
        hash = hashlib.sha1(header)
        count = 0
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'OfflineDAoC-read-only-content-audit'})
            with urllib.request.urlopen(request, timeout=90) as source, gzip.open(pending, 'wb', compresslevel=5) as destination:
                for chunk in iter(lambda: source.read(1024*1024), b''):
                    count += len(chunk)
                    assert count <= row['bytes']
                    hash.update(chunk)
                    destination.write(chunk)
            assert count == row['bytes'] and hash.hexdigest() == row['git_blob']
            pending.replace(path)
        finally:
            if pending.exists():
                pending.unlink()
        result = {'name': row['name'], 'verified': True, 'raw_bytes': count, 'stored_bytes': path.stat().st_size}
        print(json.dumps(result), flush=True)
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(one, tables))
    (root/'catacombs_world_fetch.json').write_text(json.dumps({'passed': True, 'commit': COMMIT, 'tables': result}, indent=2), encoding='utf-8')
    return {'passed': True, 'tables': len(result), 'compressed_bytes': sum((root/(row['name']+'.gz')).stat().st_size for row in tables)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    print(json.dumps(fetch(parser.parse_args().workspace)))
