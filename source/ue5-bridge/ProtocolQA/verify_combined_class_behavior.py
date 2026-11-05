"""Seal scoped Bainshee and Vampiir behavior against the same complete joint data."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_combined_vampiir_behavior import verify as verify_vampiir


def verify(workspace):
    vampiir = verify_vampiir(workspace)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    groups = {
        'class_39_level_50_training_preloaded': ['original_training_points_and_spells', 'trained_spells_survive_saved_reentry'],
        'class_39_level_50_combat_preloaded': ['normal_movement_interrupts', 'normal_player_hostile_damage_and_mana',
                                             'native_geometry_answers_server_los'],
        'class_39_level_50_effect_ward_preloaded': ['original_absorption_effect_released'],
        'class_39_level_50_effect_barrier_preloaded': ['original_absorption_effect_released'],
    }
    receipt_path = workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate/build_receipt.json'
    receipt = json.loads(receipt_path.read_text())
    proposal = json.loads((workspace/'Reports/combined_expansions/data_integration/proposal.json').read_text())
    evidence = dict(vampiir['evidence'])
    for name, checks in groups.items():
        report_path = workspace/'Reports/combined_expansions/starting_spells'/name/'real_protocol.json'
        report = json.loads(report_path.read_text())
        assert all(report.get(k) for k in ['passed', 'real_protocol', 'disposable_only', 'complete',
                    'combined_expansion_build', 'database_restored', 'candidate_server_restored', 'normal_shutdown'])
        assert not report['errors'] and report['class_id'] == 39 and report['level'] == 50
        assert report['candidate_build_receipt_sha256'] == digest(receipt_path)
        assert report['candidate_server_sha256'] == receipt['binaries_sha256']['GameServer.dll']
        preload = report['preloaded_combined_data']
        assert preload['marked_qa_only'] and not preload['activation_included']
        assert preload['proposal_sha256'] == vampiir['full_package_sha256']
        assert preload['data_rows_sha256'] == vampiir['data_rows_sha256']
        assert preload['added_rows'] == proposal['added_rows']
        assert set(report['visible_spells']) == set(report['expected_spells'])
        assert all(report['checks'][k] for k in checks+['starting_list'])
        if 'training' in name:
            assert report['training']['normal_player_privileges']
        if 'combat' in name:
            combat = report['combat']
            assert report['native_observer_exit'] == 0 and combat['normal_player_privileges']
            assert combat['health_after'] < combat['health_before'] and combat['mana_after'] < combat['mana_before']
            assert combat['native_los_answers'] and all(row['visible'] for row in combat['native_los_answers'])
        if 'effect_' in name:
            effect = report['effect_probe']
            assert effect['effect_id'] == (13515 if 'ward_' in name else 13516)
            assert any(e.get('kind') == 'release' and e.get('effect_id') == effect['effect_id']
                       and not e.get('resisted') for e in effect['events'])
        evidence[name] = digest(report_path)
    result = {'passed': True, 'joint_class_behavior_cases': len(evidence),
              'bainshee_cases': len(groups), 'vampiir_cases': vampiir['joint_vampiir_behavior_cases'],
              'build_receipt_sha256': digest(receipt_path),
              'full_package_sha256': vampiir['full_package_sha256'], 'data_rows_sha256': vampiir['data_rows_sha256'],
              'evidence': evidence, 'normal_installation_modified': False,
              'rendered_spell_visuals_accepted': False,
              'scope': 'Seven original behavior witnesses in a marked disposable fixture with the joint server and complete data. No full-class, map, sound or spell-rendering acceptance.'}
    output = workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate/verified_class_behavior.json'
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve()), indent=2))
