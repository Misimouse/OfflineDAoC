"""Seal the private four-career creation path; native playable acceptance is separate."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(workspace):
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
    (lab/'MinotaurServerCandidate/verified_creation.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(verify(args.workspace)))
