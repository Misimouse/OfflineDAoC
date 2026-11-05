"""Seal joint server regression evidence; never activate the normal installation."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(workspace, include_native_world=False):
    workspace=workspace.resolve()
    candidate=workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate'
    receipt_path=candidate/'build_receipt.json'
    receipt=json.loads(receipt_path.read_text())
    assert receipt['passed'] and not receipt['installed'] and receipt['compiled_bridge_overlay_verified']
    assert set(receipt['candidate_features'])=={'vampiir_creation','minotaur_creation'}
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name,value in receipt['binaries_sha256'].items():
        assert digest(Path(receipt['libraries'])/name)==value
    for name,row in receipt['source_variants'].items():
        assert digest(Path(receipt['source_root'])/name)==row['original_sha256']
        assert digest(Path(row['path']))==row['candidate_sha256']
    receipt_hash=digest(receipt_path)
    evidence={'build_receipt.json':receipt_hash}
    cases=0
    groups={'minotaur_original_start':({43,44,45,46},4),
            'vampiir_shar_creation':({58},6),'bainshee_creation':({39},3),
            'shar_starter_creation':({42,43,44,45,50},10)}
    for name,(classes,count) in groups.items():
        path=workspace/'Reports/combined_expansions'/name/'real_protocol.json'
        report=json.loads(path.read_text())
        assert all(report.get(k) for k in ['passed','disposable_only','real_protocol','combined_expansion_build',
                   'database_restored','appearance_profile_restored','bridge_config_restored','candidate_files_restored','normal_shutdown'])
        assert report['candidate_build_receipt_sha256']==receipt_hash
        assert len(report['cases'])==count and {c['selected_class'] for c in report['cases']}==classes
        assert all(all(c[k] for k in ['created','appearance_retained','spell_list_complete','saved_return','existing_character_reentry']) for c in report['cases'])
        if name=='shar_starter_creation':
            assert len(report['original_starter_loadouts'])==6
        if name=='minotaur_original_start':
            assert report['original_start_without_relocation'] and 'qa_connacht_relocation' not in report
            assert all(c['original_spawn_and_bind_retained'] for c in report['cases'])
        else:
            assert report['combined_choices_verified']=={'bainshee':3,'vampiir':6,'shar':12,'minotaur':4}
        evidence[name]=digest(path)
        cases+=count
    native=workspace/'ExpansionRaceLab/CombinedExpansionNativeAcceptance/equipment_only.json'
    raw=native.read_bytes();equipment=json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
    assert equipment['passed'] and equipment['checks']>=3908 and not equipment['failures']
    evidence['native_equipment']=digest(native)
    lobby=workspace/'ExpansionRaceLab/CombinedExpansionLobbyAcceptance/summary.json'
    screens=json.loads(lobby.read_text())
    assert set(screens)=={'create','customize'}
    assert all(s['passed'] and s['exit']==0 and not s['failures'] and s['minotaur_creation_tested']
               and s['shar_creation_tested'] for s in screens.values())
    evidence['native_lobby']=digest(lobby)
    inputs=lobby.parent/'inputs.json'
    native_inputs=json.loads(inputs.read_text())
    assert all(digest(Path(path))==value for path,value in native_inputs.items()),'Native lobby inputs changed'
    evidence['native_lobby_inputs']=digest(inputs)
    # Retain the full-suite failure explicitly: source-empty horn targets must
    # not disappear behind the narrower equipment/creation acceptance.
    full=workspace/'ExpansionRaceLab/CombinedExpansionNativeAcceptance/native.json'
    raw=full.read_bytes();appearance=json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
    assert appearance['failures']==['world and frozen miniature publish actual facial render weights 1419']
    evidence['native_appearance_known_limitation']=digest(full)
    result={'passed':True,'installed':False,'activated':False,'real_protocol_cases':cases,
            'native_equipment_checks':equipment['checks'],
            'native_lobby_checks':sum(s['checks'] for s in screens.values()),
            'full_native_appearance_suite_passed':False,
            'candidate_features':receipt['candidate_features'],'normal_server_sources_unchanged':True,
            'normal_database_modified':False,'evidence':evidence,
            'scope':'Joint creation, appearance, skills and saved return only; no normal installation deployment.',
            'pending':['Joint live world review','Mauler remains disabled','Original Horn Size behavior']}
    if include_native_world:
        folder=workspace/'Reports/combined_expansions/minotaur_original_start_world'
        path=folder/'real_protocol.json';world=json.loads(path.read_text())
        assert all(world.get(k) for k in ['passed','combined_expansion_build','database_restored','candidate_files_restored','normal_shutdown','native_world_original_bind_retained'])
        assert world['candidate_build_receipt_sha256']==receipt_hash
        assert len(world['cases'])==1 and world['cases'][0]['selected_class']==46
        assert world['native_world_probe']['passed'] and world['native_world_probe']['real_native_world']
        observed=json.loads((folder/'world_observed.json').read_text())
        assert observed['connected'] and observed['navigation_ready']
        gm=observed['player_status']['gm_mode']
        assert gm['ready'] and not gm['combat_test'] and not gm['uncertain'] and not gm['pending']
        assert world['native_world_probe']['gm_protected_confirmed']
        assert observed['equipment_visual']['missing_models']==observed['equipment_visual']['missing_bones']==0
        image=folder/'native_world.png';assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        result['joint_minotaur_native_world_passed']=True
        result['evidence']['native_world_protocol']=digest(path)
        result['evidence']['native_world_capture']=digest(image)
        worlds=['minotaur_original_start_world']
        for group,career in [('bainshee_creation_world',39),('vampiir_shar_creation_world',58)]:
            folder=workspace/'Reports/combined_expansions'/group
            path=folder/'real_protocol.json';world=json.loads(path.read_text())
            assert all(world.get(k) for k in ['passed','combined_expansion_build','database_restored',
                       'appearance_profile_restored','bridge_config_restored','candidate_files_restored',
                       'normal_shutdown','native_world_bind_retained'])
            assert world['candidate_build_receipt_sha256']==receipt_hash
            assert len(world['cases'])==1 and world['cases'][0]['selected_class']==career
            assert all(world['cases'][0][k] for k in ['created','appearance_retained','spell_list_complete','saved_return','existing_character_reentry'])
            assert world['native_world_probe']['passed'] and world['native_world_probe']['gm_protected_confirmed']
            observed=json.loads((folder/'world_observed.json').read_text())
            gm=observed['player_status']['gm_mode']
            assert observed['connected'] and observed['navigation_ready'] and observed['map']=='Ardee_Nwiro_Prueba_Limpieza_v01'
            assert gm['ready'] and not gm['combat_test'] and not gm['uncertain'] and not gm['pending']
            assert observed['equipment_visual']['missing_models']==observed['equipment_visual']['missing_bones']==0
            image=folder/'native_world.png';assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
            evidence[group]=digest(path);evidence[group+'_capture']=digest(image)
            worlds.append(group)
        result['joint_native_world_witnesses']=worlds
        result['scope']='Joint creation and saved return plus three native GM world-entry witnesses; advanced abilities and transformations are separate acceptance.'
        result['pending'][0]='Advanced Bainshee/Vampiir native abilities and transformation review'
    (candidate/'verified_joint_creation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--include-native-world',action='store_true')
    args=parser.parse_args();print(json.dumps(verify(args.workspace,args.include_native_world)))
