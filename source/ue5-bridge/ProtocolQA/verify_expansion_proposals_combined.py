"""Compose all three candidate spell packages in memory, preserving existing spells and class switches."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from bainshee_probe_data import install


def row_hash(row):
    return hashlib.sha256(json.dumps(dict(row), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--baseline', required=True, type=Path, help='Marked disposable baseline backup; never the played database')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--careers', action='store_true', help='Also compose the separate original career data proposals')
    args = parser.parse_args()
    root = args.workspace.resolve()
    baseline = args.baseline.resolve()
    assert baseline.is_relative_to(root / 'Backups') and args.output.resolve().is_relative_to(root / 'Reports')
    prepared = json.loads((root / 'Reports/protocol_qa/prepared.json').read_text())
    run = Path(prepared['root']).resolve()
    assert run.is_relative_to(root / 'ProtocolQA')
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    baseline_hash = hashlib.sha256(baseline.read_bytes()).hexdigest()
    with sqlite3.connect(baseline.as_uri() + '?mode=ro', uri=True) as source:
        assert source.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0] == run.name
        source.backup(db)
    assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0] == run.name
    tables = ['Spell', 'LineXSpell'] + (['Ability', 'SpecXAbility'] if args.careers else [])
    counts_before = {table: db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] for table in tables}
    protected = {str(spell_id): row_hash(db.execute('SELECT * FROM Spell WHERE SpellID=?', (spell_id,)).fetchone()) for spell_id in [13018, 13571]}
    switches_before = [tuple(row) for row in db.execute("SELECT Key,Value FROM ServerProperty WHERE Key IN ('disabled_classes','disabled_races','start_as_base_class','enable_sluaghbinder') ORDER BY Key")]
    folder = root / 'Reports/appearance'
    proposals = {39: folder / 'bainshee_probe_proposal.json', 58: folder / 'vampiir_probe_proposal.json', 62: folder / 'mauler_probe_proposal.json'}
    try:
        install(db, proposals[58], run.name, 39)
    except AssertionError:
        pass
    else:
        raise AssertionError('Wrong-class package must be rejected')
    assert counts_before == {table: db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] for table in counts_before}
    packages = [install(db, path, run.name, class_id) for class_id, path in proposals.items()]
    careers = []
    if args.careers:
        from expansion_career_data import install as install_career
        for class_id in [58, 62]:
            careers.append(install_career(db, folder / ('career_' + str(class_id) + '_proposal.json'), run.name, class_id))
    for spell_id, expected in protected.items():
        assert row_hash(db.execute('SELECT * FROM Spell WHERE SpellID=?', (int(spell_id),)).fetchone()) == expected
    switches_after = [tuple(row) for row in db.execute("SELECT Key,Value FROM ServerProperty WHERE Key IN ('disabled_classes','disabled_races','start_as_base_class','enable_sluaghbinder') ORDER BY Key")]
    assert switches_after == switches_before
    added = {table: db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] - counts_before[table] for table in counts_before}
    assert added == ({'Spell': 377, 'LineXSpell': 376, 'Ability': 4, 'SpecXAbility': 28} if args.careers else {'Spell': 369, 'LineXSpell': 376})
    aliases = [int(entry['candidate']) for package in packages for entry in package['remapped_ids'].values()]
    assert sorted(aliases) == [60000, 60001] and len(set(aliases)) == len(aliases)
    db.close()
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == baseline_hash
    report = {'passed': True, 'in_memory_only': True, 'baseline_unchanged': True,
              'played_database_opened': False, 'class_switches_preserved': True,
              'wrong_class_rejected_before_insertion': True, 'protected_spell_hashes': protected,
              'added': added, 'unique_aliases': aliases,
              'career_packages': careers,
              'packages': [{'class_id': package['class_id'], 'spells': package['new_spells'], 'links': package['line_spells']} for package in packages],
              'not_certified': ['class enablement', 'all spell semantics', 'native appearance', 'owner acceptance']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
