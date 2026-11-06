"""Prepare only the validated Hibernian Minotaur activation; retain every other restriction."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3

from prepare_combined_expansion_data import digest
from install_review_expansion_delta import fingerprint
from snapshot_world_database import snapshot
from minotaur_transport_metadata import apply as transport_metadata
from prepare_review_expansion_delta import IDENTITIES


def prepare(workspace, install):
    repo = Path(__file__).resolve().parents[3]
    lab = workspace/'ExpansionRaceLab'
    output = lab/'CentralDelivery/MinotaurActivation'
    output.mkdir(exist_ok=True)
    candidate = lab/'CombinedExpansionServerCandidate'
    receipt = json.loads((candidate/'build_receipt.json').read_text())
    proof = json.loads((candidate/'verified_joint_creation.json').read_text())
    assert proof['passed'] and proof['joint_minotaur_native_world_passed'] and proof['preloaded_joint_data_accepted']
    assert receipt['passed'] and set(receipt['candidate_features']) == {'minotaur_creation', 'vampiir_creation'}
    source = repo/'source/server/GameServer'
    rule_source = output/'RulesSource'
    shutil.copytree(source/'playerclasses', rule_source/'playerclasses', dirs_exist_ok=True)
    (rule_source/'Enums').mkdir(exist_ok=True)
    shutil.copy2(source/'Enums/eCharacterClass.cs', rule_source/'Enums/eCharacterClass.cs')
    for name, row in receipt['source_variants'].items():
        path = Path(row['path'])
        assert digest(path) == row['candidate_sha256']
        assert digest(repo/'source/server'/name) == row['original_sha256']
        target = rule_source/Path(name).relative_to('GameServer')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    pipeline = repo/'source/new-client/pipeline/build_server_classes.py'
    spec = importlib.util.spec_from_file_location('central_minotaur_rules', pipeline)
    rules = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rules)
    package_path = workspace/'Reports/combined_expansions/data_integration/proposal.json'
    package = json.loads(package_path.read_text())
    assert package['passed'] and not package['activation_included']
    original_starts = [row for row in package['rows']['StartupLocation'] if row['RaceID'] == 21]
    assert len(original_starts) == 2 and {r['ClassID'] for r in original_starts} == {52, 53}
    assert all((r['XPos'], r['YPos'], r['ZPos'], r['Region']) == (340874, 467094, 5200, 200) for r in original_starts)
    with snapshot(install/'runtime/data/opendaoc.sqlite3.db', lab/'TestTemp') as (db, metadata):
        # Use the fresh logical world, not an earlier physical main/WAL hash:
        # another reader may legitimately checkpoint WAL without changing rows.
        starts = []
        next_start_id = int(db.execute('SELECT COALESCE(MAX(StartupLoc_ID),0)+1 FROM StartupLocation').fetchone()[0])
        keys = IDENTITIES['StartupLocation']
        for original in original_starts:
            matches = db.execute('SELECT * FROM StartupLocation WHERE '+' AND '.join('"'+key+'"=?' for key in keys),
                                 [original[key] for key in keys]).fetchall()
            assert len(matches) <= 1
            if matches:
                assert all(matches[0][key] == value for key, value in original.items() if key not in ['StartupLoc_ID', 'LastTimeRowUpdated'])
            else:
                row = dict(original, StartupLoc_ID=next_start_id)
                starts.append(row)
                next_start_id += 1
        properties = dict(db.execute("SELECT Key,Value FROM ServerProperty WHERE Key IN ('disabled_classes','disabled_races','start_as_base_class','enable_sluaghbinder')"))
        disabled = rules.id_set(properties['disabled_races'])
        assert 21 in disabled and {16, 17, 18, 19, 20} <= disabled
        assert {39, 58, 62} <= rules.id_set(properties['disabled_classes'])
        after = dict(properties)
        after['disabled_races'] = ';'.join(map(str, sorted(disabled-{21})))
        memory = sqlite3.connect(':memory:')
        try:
            db.backup(memory)
            before = fingerprint(memory)
            for row in starts:
                columns = list(row)
                memory.execute('INSERT INTO StartupLocation ('+','.join('"'+k+'"' for k in columns)+') VALUES ('+','.join('?' for _ in columns)+')', list(row.values()))
            memory.execute("UPDATE ServerProperty SET Value=? WHERE Key='disabled_races'", (after['disabled_races'],))
            expected = fingerprint(memory, {'StartupLocation': starts})
            assert {k: v for k, v in expected.items() if k != 'ServerProperty'} == {k: v for k, v in before.items() if k != 'ServerProperty'}
            assert dict(memory.execute('SELECT Key,Value FROM ServerProperty')) == {**dict(db.execute('SELECT Key,Value FROM ServerProperty')), 'disabled_races': after['disabled_races']}
        finally:
            memory.close()
    tiny = output/'rules_properties.sqlite3.db'
    with sqlite3.connect(tiny) as db:
        db.execute('CREATE TABLE IF NOT EXISTS ServerProperty(Key TEXT PRIMARY KEY,Value TEXT)')
        db.execute('DELETE FROM ServerProperty')
        db.executemany('INSERT INTO ServerProperty VALUES (?,?)', after.items())
    rules.GS, rules.DB, rules.OUT = rule_source, tiny, output/'server_classes.json'
    rules.main()
    catalogue = json.loads(rules.OUT.read_text())
    current_rules = install/'new-client/godot/content/rules/server_classes.json'
    baseline = json.loads(current_rules.read_text())
    without_minotaur = copy.deepcopy(catalogue)
    for row in without_minotaur['classes'].values():
        row['races'] = [r for r in row['races'] if r != 21]
    assert without_minotaur['realms'] == baseline['realms'] and without_minotaur['classes'] == baseline['classes']
    assert {int(key) for key, row in catalogue['classes'].items() if 21 in row['races']} == {43, 44, 45, 46}
    assert catalogue['race_genders']['21'] == 'male'
    assert not any(18 in row['races'] or int(key) in [39, 58, 62] for key, row in catalogue['classes'].items())
    files = []

    def add(source, target):
        assert source.is_file()
        files.append({'source': str(source), 'target': str(target), 'after_sha256': digest(source),
                      'before_sha256': digest(target) if target.exists() else None})

    add(rules.OUT, current_rules)
    for name in ['character_appearance.gd', 'character_lobby.gd', 'gm_test_mode.gd', 'live_gateway.gd']:
        add(repo/'source/ue5-bridge/Godot'/name, workspace/'Godot'/name)
    net = install/'new-client/godot/game/net/server.gd'
    canonical_net = repo/'source/new-client/godot/game/net/server.gd'
    patched_net = output/'server.gd'
    patched_net.write_text(transport_metadata(net.read_text(encoding='utf-8-sig'), canonical_net.read_text(encoding='utf-8-sig')), encoding='utf-8')
    add(patched_net, net)
    race_root = lab/'MinotaurModularCandidate/content/characters/races/mino'
    for path in race_root.iterdir():
        if path.is_file() and path.suffix in ['.json', '.gltf']:
            add(path, install/'new-client/godot/content/characters/races/mino'/path.name)
    for name, sha in receipt['binaries_sha256'].items():
        binary = Path(receipt['libraries'])/name
        assert digest(binary) == sha
        for folder in [install/'runtime/server', install/'runtime/server/lib', install/'runtime/server/win-x64']:
            assert (folder/name).is_file()
            add(binary, folder/name)
    plan = {'passed': True, 'installed': False, 'scope': 'Hibernian Minotaur only; four original male careers. Every other race/class restriction retained.',
            'snapshot': metadata, 'properties_before': properties, 'properties_after': after,
            'before_fingerprint': before, 'source_proposal_sha256': digest(package_path),
            'startup_insert_rows': starts, 'existing_tables_verified': len(before),
            'all_existing_rows_preserved_except_disabled_races_value': True,
            'rules': catalogue, 'files': files,
            'candidate_receipt_sha256': digest(candidate/'build_receipt.json'),
            'normal_database_modified': False, 'world_population_imported': False}
    (output/'plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'startup_rows': len(starts), 'files': len(files), 'only_race_enabled': 21,
                      'classic_choices_preserved': True, 'other_expansions_still_disabled': True}))
    return plan


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--install', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.workspace.resolve(), args.install.resolve())
