"""Exercise the combined DOL data in a rolled-back, marked QA transaction only."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import socket
import sqlite3

from bainshee_probe_data import install as install_spells
from expansion_career_data import install as install_career
from prepare_hibernia_starter_repair import prepare as prepare_items
from prepare_shar_startup_proposal import prepare as prepare_starts


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(workspace):
    workspace = workspace.resolve()
    prepared = json.loads((workspace/'Reports/protocol_qa/prepared.json').read_text())
    run, database = Path(prepared['root']).resolve(), Path(prepared['database']).resolve()
    assert run.is_relative_to(workspace/'ProtocolQA') and database.is_relative_to(run)
    # Never run this transaction alongside the private protocol server.
    with socket.socket() as guard:
        # A closed Windows loopback port may time out rather than refuse a
        # connection. Binding is the direct exclusive-use test; never listen.
        guard.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        guard.bind(('127.0.0.1', 10351))
    seal = workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate/verified_joint_creation.json'
    proof = json.loads(seal.read_text())
    assert proof['passed'] and proof['joint_advanced_protocol_cases'] == 5
    assert proof['joint_live_native_form_races'] == [9, 11, 12]
    references = workspace/'References/DOLPublic_b5b29c2ada76'
    proposals = {39: workspace/'Reports/appearance/bainshee_probe_proposal.json',
                 58: workspace/'Reports/appearance/vampiir_probe_proposal.json'}
    career = workspace/'Reports/appearance/career_58_proposal.json'
    items = prepare_items(references/'ItemTemplate.json', database)
    starts = [prepare_starts(references/'StartupLocation.source.json', database, race)
              for race in [18, 21]]
    tables = ['Spell', 'LineXSpell', 'Ability', 'SpecXAbility', 'ItemTemplate', 'StartupLocation']
    rows = {name: [] for name in tables}
    for path in proposals.values():
        proposal = json.loads(path.read_text())
        rows['Spell'] += proposal['spells']
        rows['LineXSpell'] += proposal['line_spells']
    for table, values in json.loads(career.read_text())['rows'].items():
        rows[table] += values
    rows['ItemTemplate'] += items['insert_rows']
    before_bytes = database.read_bytes()
    before_hash = hashlib.sha256(before_bytes).hexdigest()
    try:
        with closing(sqlite3.connect(database)) as db:
            db.row_factory = sqlite3.Row
            assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0] == run.name
            before = {table: db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in tables}
            # The two independent startup proposals may reserve the same surrogate
            # IDs. Allocate them together without altering original spawn values.
            next_id = max(int(row[0]) for row in db.execute('SELECT StartupLoc_ID FROM StartupLocation'))+1
            for proposal in starts:
                for original in proposal['insert_rows']:
                    row = dict(original)
                    row['StartupLoc_ID'] = next_id
                    next_id += 1
                    rows['StartupLocation'].append(row)
            db.execute('SAVEPOINT combined_expansion_data')
            try:
                applied = [install_spells(db, path, run.name, class_id)
                           for class_id, path in proposals.items()]
                applied.append(install_career(db, career, run.name, 58))
                for table in ['ItemTemplate', 'StartupLocation']:
                    for row in rows[table]:
                        columns = list(row)
                        db.execute('INSERT INTO '+table+' ('+','.join('"'+k+'"' for k in columns)+') VALUES ('+
                                   ','.join('?' for _ in columns)+')', [row[k] for k in columns])
                added = {table: db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]-before[table]
                         for table in tables}
                assert added == {table: len(values) for table, values in rows.items()}
                assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
            finally:
                db.execute('ROLLBACK TO combined_expansion_data')
                db.execute('RELEASE combined_expansion_data')
            assert before == {table: db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in tables}
    finally:
        # SQLite can retain physical page/header changes after logical rollback.
        # The marked fixture is offline; restore its exact bytes after closing.
        database.write_bytes(before_bytes)
    assert digest(database) == before_hash, 'QA database bytes changed after rolled-back integration'
    result = {'passed': True, 'proposal_only': True, 'installed': False,
              'database_restored_byte_for_byte': True, 'normal_database_modified': False,
              'activation_included': False, 'source_commit': 'b5b29c2ada7695414b94f5fa110eb505a477d007',
              'inputs': {str(path): digest(path) for path in [seal, *proposals.values(), career]},
              'added_rows': added, 'rows': rows, 'spell_and_career_application': applied,
              'startup_references': [proposal['reference'] for proposal in starts],
              'limitations': ['No race/class activation or inventory grants',
                              'Shar original starts need a map beyond Connacht',
                              'Pinned DOL reference has no bainshee_item promotion gift',
                              'Mauler remains excluded']}
    output = workspace/'Reports/combined_expansions/data_integration/proposal.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return {'passed': True, 'installed': False, 'added_rows': added,
            'database_restored_byte_for_byte': True, 'proposal': str(output)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    print(json.dumps(prepare(parser.parse_args().workspace)))
