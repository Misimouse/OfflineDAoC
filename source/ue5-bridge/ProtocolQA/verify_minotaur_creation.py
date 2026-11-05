"""Seal the private four-career creation path; native playable acceptance is separate."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(workspace, include_promotion=False, include_original_start=False):
    workspace=workspace.resolve()
    lab=workspace/'ExpansionRaceLab'
    creation=workspace/'Reports/minotaur_creation/real_protocol.json'
    build=lab/'MinotaurServerCandidate/build_receipt.json'
    source=lab/'MinotaurModularCandidate/verified.json'
    report=json.loads(creation.read_text())
    assert report['passed'] and report['real_protocol'] and report['disposable_only']
    assert all(report[k] for k in ['database_restored','appearance_profile_restored','bridge_config_restored','candidate_files_restored','normal_shutdown'])
    assert report['candidate_build_receipt_sha256']==hashlib.sha256(build.read_bytes()).hexdigest()
    candidate=json.loads(build.read_text())
    assert candidate['candidate_features']==['minotaur_creation'] and not candidate['installed']
    for name,row in candidate['source_variants'].items():
        assert hashlib.sha256((Path(candidate['source_root'])/name).read_bytes()).hexdigest()==row['original_sha256']
        assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['candidate_sha256']
    for name,digest in candidate['binaries_sha256'].items():
        assert hashlib.sha256((Path(candidate['libraries'])/name).read_bytes()).hexdigest()==digest
    art=json.loads(source.read_text())
    assert art['passed'] and not art['installed'] and not art['activated']
    cases=report['cases']
    assert len(cases)==4 and {c['selected_class'] for c in cases}=={43,44,45,46}
    assert len({tuple(sorted(c['original_saved_appearance_bytes'].items())) for c in cases})==4
    for case in cases:
        assert case['figure']=='mino' and case['world_model']==1419 and case['level']==1
        assert case['base_class']==(53 if case['selected_class']==46 else 52)
        assert all(case[k] for k in ['created','appearance_retained','spell_list_complete','saved_return','existing_character_reentry'])
        assert len(case['look']['sliders'])==1
    result={'passed':True,'installed':False,'activated':False,'careers_tested':4,
            'original_appearance_packet_bytes_saved':True,'normal_data_untouched':True,
            'native_playable_creation_accepted':False,'mauler_enabled':False,
            'evidence':{str(p.relative_to(workspace)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [creation,build,source]},
            'pending':['Native creation/customization UI','Native modular equipment and helmets','Original trainer promotion']}
    if include_promotion:
        path=workspace/'Reports/minotaur_promotion/real_protocol.json'
        promotion=json.loads(path.read_text())
        assert promotion['passed'] and promotion['real_protocol'] and promotion['disposable_only']
        assert all(promotion[k] for k in ['database_restored','appearance_profile_restored','bridge_config_restored','candidate_files_restored','normal_shutdown'])
        assert promotion['candidate_build_receipt_sha256']==hashlib.sha256(build.read_bytes()).hexdigest()
        assert len(promotion['cases'])==4 and {c['selected_class'] for c in promotion['cases']}=={43,44,45,46}
        for case in promotion['cases']:
            assert case['level']==5 and case['figure']=='mino' and case['world_model']==1419
            assert all(case[k] for k in ['original_trainer_promotion','advanced_class_retained','saved_return','existing_character_reentry','spell_list_complete','appearance_retained'])
        result['promotion_cases']=4
        result['evidence'][str(path.relative_to(workspace))]=hashlib.sha256(path.read_bytes()).hexdigest()
        result['pending'].remove('Original trainer promotion')
    if include_original_start:
        path=workspace/'Reports/minotaur_original_start/real_protocol.json'
        start=json.loads(path.read_text())
        assert start['passed'] and start['real_protocol'] and start['disposable_only']
        assert all(start[k] for k in ['database_restored','appearance_profile_restored','bridge_config_restored','candidate_files_restored','normal_shutdown','original_start_without_relocation'])
        assert 'qa_connacht_relocation' not in start and len(start['cases'])==4
        assert {c['selected_class'] for c in start['cases']}=={43,44,45,46}
        assert all(c['original_spawn_and_bind_retained'] and c['original_start_zone']==207 and c['existing_character_reentry'] for c in start['cases'])
        result['original_start_cases']=4
        result['original_start_zone']=207
        result['evidence'][str(path.relative_to(workspace))]=hashlib.sha256(path.read_bytes()).hexdigest()
    (lab/'MinotaurServerCandidate/verified_creation.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--include-promotion',action='store_true')
    parser.add_argument('--include-original-start',action='store_true')
    args=parser.parse_args()
    print(json.dumps(verify(args.workspace,args.include_promotion,args.include_original_start)))
