"""Seal source/export/native-import evidence without claiming playable acceptance."""
import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from minotaur_source_parts import resolve_parts


def verify(candidate, client, official_archive):
    candidate, client, official_archive = (p.resolve() for p in (candidate, client, official_archive))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'new-client/pipeline'))
    from daoc_mpk import read_mpk
    conversion = json.loads((candidate/'conversion.json').read_text())
    assert conversion['passed'] and conversion['source_archive_unchanged']
    assert not conversion['installed'] and not conversion['activated']
    assert hashlib.sha256((client/'gamedata.mpk').read_bytes()).hexdigest() == conversion['original_archive_sha256']
    original = read_mpk(str(client/'gamedata.mpk'))
    official = read_mpk(str(official_archive))
    def parts(tables):
        return resolve_parts(list(csv.reader(io.StringIO(tables['fig3parts.csv'].decode('latin1')))))
    _, installed_aliases = parts(original)
    _, official_aliases = parts(official)
    assert installed_aliases == official_aliases == conversion['fractional_source_ids']
    assert len(installed_aliases) == 69
    report = {'passed': False, 'installed': False, 'activated': False,
              'playable_creation_accepted': False, 'source_archive_unchanged': True,
              'fractional_rows_match_official_source': 69, 'evidence': {}}
    for relative in ['conversion.json', 'figure_exports_verified.json', 'appearance_exports_verified.json',
                     'native_import.json', 'Reports/appearance/import_parts.json',
                     'Reports/appearance/prepare_materials.json', 'native_render.json']:
        path = candidate/relative
        raw = path.read_bytes()
        document = json.loads(raw)
        assert document['passed'] and not document['installed'], relative
        report['evidence'][relative] = hashlib.sha256(raw).hexdigest()
    figure = json.loads((candidate/'figure_exports_verified.json').read_text())['models']['1419']
    assert figure['original_clips'] == conversion['clips'] == 213
    assert figure['joints'] == 108 and figure['vertices'] > 0
    appearance = json.loads((candidate/'appearance_exports_verified.json').read_text())
    assert appearance['parts'] == 11 and appearance['morph_targets'] == 42
    native = json.loads((candidate/'Reports/appearance/import_parts.json').read_text())
    assert len(native['parts']) == 11 and native['morph_targets'] == 42
    assert not native['active_catalogues_changed']
    meta = json.loads(Path(conversion['metadata']).read_text())
    assert len(meta['faces']) == 7 and len(meta['eyes']) == 8 and len(meta['skin_tones']) == 8
    assert len(meta['hair_styles']) == 10 and [s['label'] for s in meta['sliders']] == ['Horn Size']
    capture = candidate/'native_body.png'
    assert capture.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'
    report['evidence']['native_body.png'] = hashlib.sha256(capture.read_bytes()).hexdigest()
    report['official_archive_sha256'] = hashlib.sha256(official_archive.read_bytes()).hexdigest()
    report['passed'] = True
    (candidate/'verified.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['candidate', 'client', 'official-archive']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.candidate, args.client, args.official_archive)))
