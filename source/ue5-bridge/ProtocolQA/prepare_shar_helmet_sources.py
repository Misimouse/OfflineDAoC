"""Convert all original Shar helmet references into a private lab, without upscaling."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys


def prepare(client, lab):
    client, lab = client.resolve(), lab.resolve()
    assert client.is_dir() and lab.is_dir() and not lab.is_relative_to(client)
    sys.path.insert(0, str(lab / 'PythonDeps'))
    pipeline = Path(__file__).resolve().parents[2] / 'new-client/pipeline'
    sys.path.insert(0, str(pipeline))
    os.environ['DAOC_CLIENT'] = str(client)
    from daoc_mpk import read_mpk
    import build_helms as converter
    archive = client / 'gamedata.mpk'
    before = hashlib.sha256(archive.read_bytes()).hexdigest()
    tables = read_mpk(str(archive))
    rows = lambda name: list(csv.reader(io.StringIO(tables[name].decode('latin1'))))
    objects = rows('objects.csv')
    header = objects[1]
    items = {r[0]: r for r in rows('items.csv') if r and r[0].isdigit()}
    columns = [header.index('Nif' + str(i)) for i in range(1, 13)]
    ordinary, full = [], []
    for row in objects:
        if not row or not row[0].isdigit():
            continue
        if any(c < len(row) and row[c] in items and items[row[c]][2].lower().endswith(('_sha_m', '_sha_f')) for c in columns):
            ordinary.append(int(row[0]))
        elif len(row) > 96 and row[96].strip() == '1' and row[95].strip().isdigit() and 1 <= int(row[95]) <= 12:
            full.append(int(row[0]))
    models = sorted(set(ordinary + full))
    assert ordinary and full
    converter.OUT = lab / 'GodotHelmetSourcesFull'
    converter.FIG_TEX = lab / 'FullHelmetTexturesFull'
    converter.PREFIXES = ['sha']
    converter.wanted_models = lambda: models
    class ExactAppliedTexturesOnly:
        def image(self, name):
            raise RuntimeError('Original applied texture unresolved; do not substitute: ' + name)
    converter.TextureIndex = ExactAppliedTexturesOnly
    copies = []
    def copy_originals(source, destination, factor_after=4):
        destination.mkdir(parents=True, exist_ok=True)
        for path in source.glob('*.png'):
            target = destination / path.name
            shutil.copy2(path, target)
            assert path.read_bytes() == target.read_bytes()
            copies.append(str(path))
    converter.upscale_dir = copy_originals
    converter.main()
    result = json.loads((converter.OUT / 'helms.json').read_text(encoding='utf-8-sig'))
    assert not result['missing'] and set(result['models']) == {str(i) for i in models}
    assert all('full' in entry or set(entry) == {'sha_m', 'sha_f'} for entry in result['models'].values())
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == before
    report = {'passed': True, 'installed': False, 'original_archive_sha256': before, 'ordinary_models': ordinary,
              'full_models': full, 'models': models, 'original_png_copies': len(copies), 'upscaled': False,
              'catalogue': str(converter.OUT / 'helms.json'), 'original_client_modified': False}
    (lab / 'shar_helmet_sources_full.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--lab', type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.client, args.lab)
    print(json.dumps({'passed': report['passed'], 'models': len(report['models']), 'installed': False}))
