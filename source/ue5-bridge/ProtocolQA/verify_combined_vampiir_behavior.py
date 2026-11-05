"""Seal scoped Vampiir behavior evidence from the full joint package, without deployment."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(workspace):
    candidate = workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate'
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    receipt_path = candidate/'build_receipt.json'
    receipt = json.loads(receipt_path.read_text())
    assert receipt['passed'] and not receipt['installed'] and receipt['compiled_bridge_overlay_verified']
    assert set(receipt['candidate_features']) == {'vampiir_creation', 'minotaur_creation'}
    for name, expected in receipt['binaries_sha256'].items():
        assert digest(Path(receipt['libraries'])/name) == expected
    proposal_path = workspace/'Reports/combined_expansions/data_integration/proposal.json'
    proposal = json.loads(proposal_path.read_text())
    assert proposal['passed'] and proposal['proposal_only'] and not proposal['installed']
    assert not proposal['activation_included'] and not proposal['normal_database_modified']
    rows_digest = hashlib.sha256(json.dumps(proposal['rows'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    groups = {
        'class_58_level_50_career_power_preloaded': ['original_combat_power_generation'],
        'class_58_level_50_training_self_buff_career_preloaded': ['original_training_points_and_spells',
                    'trained_self_buff_power_and_effect', 'trained_spells_survive_saved_reentry'],
        'class_58_level_50_career_bolt_preloaded': ['unseen_target_flag_blocks_instant_bolt',
                    'original_ability_power_bolt_and_native_los'],
    }
    evidence = {}
    for name, checks in groups.items():
        folder = workspace/'Reports/combined_expansions/starting_spells'/name
        report_path = folder/'real_protocol.json'
        report = json.loads(report_path.read_text())
        assert all(report.get(k) for k in ['passed', 'real_protocol', 'disposable_only', 'complete',
                    'combined_expansion_build', 'database_restored', 'candidate_server_restored', 'normal_shutdown'])
        assert not report['errors']
        assert report['candidate_build_receipt_sha256'] == digest(receipt_path)
        assert report['candidate_server_sha256'] == receipt['binaries_sha256']['GameServer.dll']
        preload = report['preloaded_combined_data']
        assert preload['marked_qa_only'] and not preload['activation_included']
        assert preload['proposal_sha256'] == digest(proposal_path)
        assert preload['data_rows_sha256'] == rows_digest
        assert preload['added_rows'] == proposal['added_rows']
        assert set(report['visible_spells']) == set(report['expected_spells'])
        assert all(report['checks'][k] for k in checks+['starting_list', 'original_career_abilities_received'])
        if 'power_preloaded' in name:
            power = report['combat_power']
            assert power['normal_player_privileges'] and power['no_resource_grants'] and power['initial_mana'] == 0
            assert power['walked_out_of_melee_before_quit'] and any(row['mana']>0 for row in power['samples'])
        if 'training' in name:
            assert report['training']['normal_player_privileges']
        if 'bolt' in name:
            bolt = report['vampiir_bolt']
            assert report['native_observer_exit'] == 0 and bolt['normal_player_privileges']
            assert bolt['initial_mana'] == 0 and bolt['mana_after'] > 0 and bolt['native_probes']
            assert not bolt['rendered_visual_acceptance']
        evidence[name] = digest(report_path)
    result = {'passed': True, 'joint_vampiir_behavior_cases': len(groups),
              'full_package_sha256': digest(proposal_path), 'data_rows_sha256': rows_digest,
              'build_receipt_sha256': digest(receipt_path), 'evidence': evidence,
              'normal_installation_modified': False, 'rendered_spell_visuals_accepted': False,
              'scope': 'Original training, power generation/consumption, self buff, saved learned spells and instant power bolt with native visibility probe. Not full class or VFX acceptance.'}
    (candidate/'verified_vampiir_behavior.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve()), indent=2))
