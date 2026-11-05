"""Read original realm/helmet tables without converting or modifying game assets.

An audit passing means the source was inspected consistently, not that helmets
are playable. Unreferenced item rows must never become guessed equipment IDs.
"""
import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path


REALMS = [('Albion', '863', '61'), ('Midgard', '867', '62'),
          ('Hibernia', '868', '63')]


def inspect(archive):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'new-client/pipeline'))
    from daoc_mpk import read_mpk
    raw_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    tables = read_mpk(str(archive))

    def rows(name):
        return list(csv.reader(io.StringIO(tables[name].decode('latin1'))))

    monnifs, mapping = rows('monnifs.csv'), rows('fig3map.csv')
    realms = {}
    for realm, source_id, figure in REALMS:
        matches = [r for r in monnifs if r and r[0].strip() == source_id]
        assert len(matches) == 1, (realm, 'ambiguous monnifs identity')
        row = matches[0]
        assert 'Minotaur' in row[1] and row[2] == 'mino' and row[13] == figure
        parts = {int(r[1] or 0): [int(v) for v in r[3:] if v.strip().isdigit() and int(v)]
                 for r in mapping if r and r[0].strip() == figure}
        assert set(parts) == set(range(9)), (realm, 'review changed figure slots')
        assert len(parts[8]) == 10 and len(parts[7]) == 3
        realms[realm] = {'monnifs_id': int(source_id), 'figure_id': int(figure),
                         'animation_set': int(row[3]), 'part_slots': parts,
                         'full_helmet_slot_present': 9 in parts}
    assert len({tuple(v['part_slots'][8]) for v in realms.values()}) == 3
    assert len({tuple(v['part_slots'][7]) for v in realms.values()}) == 3

    items = {r[0].strip(): r for r in rows('items.csv') if r and r[0].strip().isdigit()}
    helmets = {key: r for key, r in items.items() if len(r) > 2 and r[2].lower().endswith('_min_m')}
    assert len(helmets) == 10, 'Review changed Minotaur helmet source set'
    objects = rows('objects.csv')
    nif_columns = [objects[1].index('Nif' + str(i)) for i in range(1, 13)]
    references = {key: [] for key in helmets}
    for row in objects:
        if not row or not row[0].strip().isdigit():
            continue
        for column in nif_columns:
            value = row[column].strip() if len(row) > column else ''
            if value in references:
                references[value].append({'object_id': int(row[0]), 'column': column})
        # The explicitly marked Minotaur mask path uses the classic item
        # column, not the twelve per-race Catacombs columns.
        if len(row) > 97 and row[97].strip() == '1' and row[2].strip() in references:
            references[row[2].strip()].append({'object_id': int(row[0]), 'column': 2,
                                              'noarmor_helm': True, 'skin_id': int(row[12])})
    helmet_rows = []
    for key, row in helmets.items():
        nif = archive.parent / 'items' / (row[2] + '.nif')
        helmet_rows.append({'item_id': int(key), 'name': row[2],
                            'hair_mode': int(row[23] or 0),
                            'object_references': references[key],
                            'nif_present': nif.is_file(),
                            'nif_sha256': hashlib.sha256(nif.read_bytes()).hexdigest() if nif.is_file() else None})
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == raw_hash
    return {'archive_sha256': raw_hash, 'archive_unchanged': True,
            'realms': realms, 'helmet_items': helmet_rows,
            'mask_equipment_mapping_resolved': all(references[key] for key, row in helmets.items()
                                                   if row[2].lower().startswith('mask_')),
            'helmet_equipment_mapping_resolved': all(references.values()),
            'helmet_runtime_accepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--official-archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    archive = args.client.resolve() / 'gamedata.mpk'
    output = args.output.resolve()
    assert not output.is_relative_to(args.client.resolve()), 'Keep reports outside original client'
    report = inspect(archive)
    assert all(r['nif_present'] for r in report['helmet_items']), 'Missing original Minotaur item NIF'
    if args.official_archive:
        official = inspect(args.official_archive.resolve())
        # The small official probe contains catalogues only, not item meshes.
        signature = lambda d: (d['realms'], [(r['item_id'], r['name'], r['hair_mode'],
                                            r['object_references']) for r in d['helmet_items']])
        assert signature(report) == signature(official), 'Installed/official source disagreement'
        report['official_archive_sha256'] = official['archive_sha256']
        report['official_tables_match'] = True
    report.update(audit_passed=True, installed=False, activated=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['audit_passed', 'installed', 'activated',
                                          'helmet_equipment_mapping_resolved', 'helmet_runtime_accepted']}))


if __name__ == '__main__':
    main()
