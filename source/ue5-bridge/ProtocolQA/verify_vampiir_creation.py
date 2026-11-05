"""Verify private Vampiir creation, original trainer promotion and level-six career admission."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(workspace):
    workspace = workspace.resolve()
    evidence = []
    def read(relative):
        path = workspace/relative
        assert path.resolve().is_relative_to(workspace)
        report = json.loads(path.read_text(encoding='utf-8-sig'))
        assert report['passed'], relative
        evidence.append({'path':str(path), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        return report
    receipt = read('ExpansionRaceLab/VampiirServerCandidate/build_receipt.json')
    assert not receipt['installed'] and receipt['compiled_bridge_overlay_verified']
    assert receipt['candidate_features'] == ['vampiir_creation']
    variant = receipt['source_variants']['GameServer/GlobalConstants.cs']
    original = Path(receipt['source_root'])/'GameServer/GlobalConstants.cs'
    assert hashlib.sha256(original.read_bytes()).hexdigest() == variant['original_sha256']
    for name, expected in receipt['binaries_sha256'].items():
        assert hashlib.sha256((Path(receipt['libraries'])/name).read_bytes()).hexdigest() == expected
    created = read('Reports/vampiir_creation/real_protocol.json')
    assert created['database_restored'] and created['normal_shutdown'] and created['appearance_profile_restored']
    assert created['private_vampiir_source_variant_verified'] and len(created['cases']) == 4
    assert {case['figure'] for case in created['cases']} == {'cel_m','cel_f','lur_m','lur_f'}
    assert all(case['selected_class']==58 and case['base_class']==54 and case['level']==1 and case['existing_character_reentry'] and case['appearance_retained'] and case['spell_list_complete'] for case in created['cases'])
    stats = {152,153,154,155}
    promotions = []
    for race in [9,12]:
        for sex in ['male','female']:
            report = read('Reports/starting_spells/class_58_level_5_promotion_race_'+str(race)+'_'+sex+'/real_protocol.json')
            assert report['database_restored'] and report['normal_shutdown'] and report['candidate_server_restored']
            assert report['candidate_server_sha256'] == receipt['binaries_sha256']['GameServer.dll']
            assert report['class_id']==58 and report['level']==5 and report['complete']
            assert report['checks']['original_trainer_promotes_stalker'] and report['checks']['vampiir_class_and_spells_survive_saved_reentry']
            abilities = {int(row['id']) for row in report['career_abilities']}
            assert 341 in abilities and not stats & abilities
            promotions.append({'race':race,'sex':sex,'spells':report['expected_spells']})
    boundary = read('Reports/starting_spells/class_58_level_6_career/real_protocol.json')
    assert boundary['database_restored'] and boundary['normal_shutdown'] and boundary['complete']
    assert boundary['class_id']==58 and boundary['level']==6
    assert stats | {341} <= {int(row['id']) for row in boundary['career_abilities']}
    assert boundary['checks']['vampiir_class_and_spells_survive_saved_reentry']
    regression = read('Reports/starting_spells/class_39_level_5_promotion/real_protocol.json')
    assert regression['database_restored'] and regression['normal_shutdown'] and regression['complete']
    assert regression['checks']['original_trainer_promotes_magician'] and regression['checks']['promotion_replaces_base_spell_list']
    report = {'passed':True,'installed':False,'creation_cases':4,'promotion_cases':promotions,
              'level_six_stat_boundary_passed':True,'bainshee_promotion_regression_passed':True,
              'evidence':evidence,'scope':'Private Celt/Lurikeen Vampiir acceptance only. Combined Shar eligibility, native creation presentation and normal activation are separate gates.'}
    output = workspace/'ExpansionRaceLab/VampiirAcceptance/verified.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    report=verify(parser.parse_args().workspace)
    print(json.dumps({key:report[key] for key in ['passed','installed','creation_cases','level_six_stat_boundary_passed','bainshee_promotion_regression_passed']}))
