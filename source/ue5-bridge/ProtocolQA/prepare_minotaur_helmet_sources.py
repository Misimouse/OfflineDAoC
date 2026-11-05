"""Convert explicitly marked original Minotaur masks into a private candidate.

objects.csv NoArmor Helm=1 selects the item in column 2, unlike ordinary
Catacombs helmets in Nif1..Nif12. Keep this accommodation outside the shared
converter. Head pumpkin uses a different effect path and is not a mask NIF.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
from pathlib import Path


def mask_references(objects, items):
    assert objects[1][97] == 'NoArmor Helm'
    result = {}
    for row in objects:
        if not row or not row[0].strip().isdigit() or len(row) <= 97 or row[97].strip() != '1':
            continue
        item = items.get(row[2].strip())
        if item and len(item) > 2 and item[2].lower().endswith('_min_m'):
            assert item[2].lower().startswith('mask_'), 'Review additional Minotaur helmet family'
            assert row[12].strip().isdigit() and int(row[12]) > 0
            result[int(row[0])] = {'item_id': int(row[2]), 'name': item[2],
                                   'skin_id': int(row[12]), 'source_column': 2,
                                   'noarmor_helm': True}
    return result


def prepare(client, lab):
    client, lab = client.resolve(), lab.resolve()
    assert lab.name == 'ExpansionRaceLab' and lab.is_dir() and not lab.is_relative_to(client)
    target = lab/'MinotaurHelmetCandidate'
    target.mkdir(exist_ok=True)
    assert target.resolve().is_relative_to(lab)
    sys.path.insert(0, str(lab/'PythonDeps'))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'new-client/pipeline'))
    os.environ['DAOC_CLIENT'] = str(client)
    from daoc_mpk import read_mpk
    import build_helms as converter
    archive = client/'gamedata.mpk'
    before = hashlib.sha256(archive.read_bytes()).hexdigest()
    tables = read_mpk(str(archive))
    rows = lambda name: list(csv.reader(io.StringIO(tables[name].decode('latin1'))))
    objects = rows('objects.csv')
    items = {r[0].strip(): r for r in rows('items.csv') if r and r[0].strip().isdigit()}
    references = mask_references(objects, items)
    assert len(references) == 13, 'Review changed original mask catalogue'
    nif1 = objects[1].index('Nif1')
    texture = objects[1].index('Nif12')+1
    # Adapt only the converter's private in-memory view. Keep the original item
    # IDs and the specific Helm skin (including bird/leopard/tracery/glyphs).
    for row in objects:
        if row and row[0].isdigit() and int(row[0]) in references:
            row[nif1] = row[2]
            row[texture] = row[12]
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator='\r\n').writerows(objects)
    adapted = dict(tables, **{'objects.csv': buffer.getvalue().encode('latin1')})
    converter.read_mpk = lambda path: adapted if Path(path).resolve() == archive else read_mpk(path)
    converter.OUT = target/'Sources'
    converter.FIG_TEX = target/'FigureTextures'
    converter.PREFIXES = ['min']
    converter.wanted_models = lambda: sorted(references)

    class ExactTextures:
        def image(self, name):
            raise RuntimeError('Missing exact original mask texture: '+name)

    converter.TextureIndex = ExactTextures

    def copy_originals(source, destination, factor_after=4):
        destination.mkdir(parents=True, exist_ok=True)
        for path in source.glob('*.png'):
            shutil.copy2(path, destination/path.name)
            assert path.read_bytes() == (destination/path.name).read_bytes()

    converter.upscale_dir = copy_originals
    converter.main()
    catalogue = converter.OUT/'helms.json'
    data = json.loads(catalogue.read_text())
    assert not data['missing'] and set(data['models']) == {str(i) for i in references}
    for entry in data['models'].values():
        assert set(entry) == {'min_m'}
        entry['mino'] = entry.pop('min_m')  # Original figure prefix has no gender suffix.
    catalogue.write_text(json.dumps(data, indent=2), encoding='utf-8')
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == before
    report = {'passed': True, 'installed': False, 'activated': False,
              'native_accepted': False, 'source_archive_unchanged': True,
              'source_archive_sha256': before, 'source_references': references,
              'catalogue': str(catalogue), 'upscaled': False,
              'unsupported_source_families': ['Head pumpkin effect', 'Yule hat (no equipment mapping)'],
              'ordinary_helmets_visible': False,
              'official_behavior_reference': 'https://www.darkageofcamelot.com/1125-live-patch-notes/'}
    (target/'conversion.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--lab', type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.client, args.lab)
    print(json.dumps({'passed': report['passed'], 'models': len(report['source_references']), 'installed': False}))
