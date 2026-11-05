"""Seal joint server regression evidence; never activate the normal installation."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(workspace, include_native_world=False, include_advanced_protocol=False, include_live_forms=False, include_preloaded_data=False,
           include_class_behavior=False, include_private_review=False):
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
    if include_advanced_protocol:
        groups={
            'class_39_level_5_promotion':['original_trainer_promotes_magician','promotion_replaces_base_spell_list','bainshee_class_and_spells_survive_saved_reentry'],
            'class_58_level_5_promotion_race_18_female':['original_trainer_promotes_stalker','original_career_abilities_received','vampiir_class_and_spells_survive_saved_reentry'],
            'class_39_level_5_form_cycle':['positive_buff_retains_original_form','original_offensive_cast_transforms','original_timer_restores_appearance_and_inventory'],
            'class_39_level_5_form_cycle_race_11':['positive_buff_retains_original_form','original_offensive_cast_transforms','original_timer_restores_appearance_and_inventory'],
            'class_39_level_5_form_cycle_race_12':['positive_buff_retains_original_form','original_offensive_cast_transforms','original_timer_restores_appearance_and_inventory']}
        for group,checks in groups.items():
            path=workspace/'Reports/combined_expansions/starting_spells'/group/'real_protocol.json'
            row=json.loads(path.read_text())
            assert all(row.get(k) for k in ['passed','real_protocol','disposable_only','combined_expansion_build','complete','database_restored','candidate_server_restored','normal_shutdown'])
            assert row['candidate_build_receipt_sha256']==receipt_hash
            assert row['candidate_server_sha256']==receipt['binaries_sha256']['GameServer.dll']
            assert set(row['visible_spells'])==set(row['expected_spells'])
            assert all(row['checks'][key] for key in checks)
            if 'form_cycle' in group:
                assert row['qa_native_catalogue_restored'] and 25<=row['form_timer_seconds']<=40
                assert row['form_model']=={9:1883,11:1885,12:1884}[row['race']]
            evidence[group]=digest(path)
        result['joint_advanced_protocol_cases']=len(groups)
        result['advanced_native_rendering_accepted']=False
        result['pending'][0]='Advanced native transformation rendering and complete expansion data deployment'
    if include_live_forms:
        assert include_advanced_protocol and include_native_world
        forms=[]
        catalogue=json.loads((workspace/'ExpansionRaceLab/MinotaurOwnerReview/models.json').read_text())
        for race,model in [(9,1883),(11,1885),(12,1884)]:
            group='class_39_level_5_form_cycle'+('_race_'+str(race) if race!=9 else '')+'_native'
            folder=workspace/'Reports/combined_expansions/starting_spells'/group
            path=folder/'real_protocol.json';row=json.loads(path.read_text())
            assert all(row.get(k) for k in ['passed','real_protocol','disposable_only','combined_expansion_build','complete','database_restored','candidate_server_restored','qa_native_catalogue_restored','normal_shutdown'])
            assert row['candidate_build_receipt_sha256']==receipt_hash and row['native_observer_exit']==0
            assert row['checks']['live_native_body_and_portrait_transform'] and row['checks']['live_native_original_body_and_equipment_restored']
            assert row['race']==race and row['form_model']==model and 25<=row['form_timer_seconds']<=40
            stages={name:json.loads((folder/('native_'+name+'.json')).read_text())['player_visual'] for name in ['before','transformed','restored']}
            before,changed,after=(stages[name] for name in ['before','transformed','restored'])
            assert all(v['body_visible'] and v['body_asset']==v['portrait_asset'] for v in stages.values())
            assert changed['body_asset']==catalogue[str(model)]['asset'] and changed['weapon_components']==0
            assert before['body_asset']==after['body_asset'] and before['weapon_components']==after['weapon_components']>0
            assert changed['body_asset']!=before['body_asset']
            evidence[group]=digest(path)
            for name in stages:evidence[group+'_'+name]=digest(folder/('native_'+name+'.json'))
            assert row['checks']['native_form_inputs_unchanged']
            assert all(digest(Path(path))==value for path,value in row['native_form_inputs'].items())
            for index,name in enumerate(['before','transformed','restored'],1):
                shot=folder/('visual_stage_'+str(index)+'_'+str(stages[name]['model_id'])+'.png')
                assert shot.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
                evidence[group+'_'+name+'_capture']=digest(shot)
            forms.append(race)
        result['joint_live_native_form_races']=forms
        result['bainshee_live_native_forms_accepted']=True
        result['scope']='Joint creation, saved return, native GM entry and three live Bainshee form cycles; no normal activation or complete expansion ability acceptance.'
        result['pending'][0]='Complete expansion data deployment; other advanced abilities remain separately scoped'
    if include_preloaded_data:
        assert include_live_forms
        folder=workspace/'Reports/combined_expansions/data_integration'
        package_path=folder/'proposal.json';package=json.loads(package_path.read_text())
        assert package['passed'] and package['proposal_only'] and not package['installed'] and not package['activation_included']
        assert package['database_restored_byte_for_byte'] and not package['normal_database_modified']
        assert package['added_rows']=={'Spell':254,'LineXSpell':253,'Ability':4,'SpecXAbility':19,'ItemTemplate':6,'StartupLocation':5}
        assert all(digest(Path(path))==value for path,value in package['inputs'].items())
        payload_hash=hashlib.sha256(json.dumps(package['rows'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        rollback_path=folder/'rollback_checks.json';rollback=json.loads(rollback_path.read_text())
        assert rollback['passed'] and rollback['in_memory_only'] and rollback['source_backup_unchanged']
        assert len(rollback['checks'])==4 and rollback['proposal_sha256']==digest(package_path)
        evidence['preloaded_data_proposal']=digest(package_path);evidence['preloaded_rollback_checks']=digest(rollback_path)
        counts=0
        groups={
            'minotaur_original_start_preloaded':(4,{43,44,45,46}),
            'shar_promotion_preloaded':(10,{42,43,44,45,50})}
        for group,(count,classes) in groups.items():
            path=workspace/'Reports/combined_expansions'/group/'real_protocol.json';row=json.loads(path.read_text())
            assert all(row.get(k) for k in ['passed','combined_expansion_build','database_restored','appearance_profile_restored','bridge_config_restored','candidate_files_restored','normal_shutdown'])
            assert row['candidate_build_receipt_sha256']==receipt_hash
            assert len(row['cases'])==count and {c['selected_class'] for c in row['cases']}==classes
            assert all(c['created'] and c['existing_character_reentry'] and c['spell_list_complete'] for c in row['cases'])
            assert row['preloaded_combined_data']['data_rows_sha256']==payload_hash
            if group.startswith('minotaur'):assert row['original_start_without_relocation'] and all(c['original_spawn_and_bind_retained'] for c in row['cases'])
            else:assert all(c['original_trainer_promotion'] and c['advanced_class_retained'] for c in row['cases'])
            evidence[group]=digest(path);counts+=count
        for group,key in [('class_39_level_5_promotion_preloaded','bainshee_class_and_spells_survive_saved_reentry'),
                          ('class_58_level_5_promotion_race_18_female_preloaded','vampiir_class_and_spells_survive_saved_reentry'),
                          ('class_39_level_5_form_cycle_native_preloaded','live_native_original_body_and_equipment_restored')]:
            path=workspace/'Reports/combined_expansions/starting_spells'/group/'real_protocol.json';row=json.loads(path.read_text())
            assert all(row.get(k) for k in ['passed','complete','combined_expansion_build','database_restored','candidate_server_restored','normal_shutdown'])
            assert row['candidate_build_receipt_sha256']==receipt_hash
            assert row['preloaded_combined_data']['data_rows_sha256']==payload_hash
            assert row['checks'][key] and set(row['expected_spells'])==set(row['visible_spells'])
            if 'native' in group:
                assert row['native_observer_exit']==0 and row['checks']['live_native_body_and_portrait_transform']
                assert row['checks']['native_form_inputs_unchanged'] and all(digest(Path(path))==value for path,value in row['native_form_inputs'].items())
            evidence[group]=digest(path);counts+=1
        result['preloaded_joint_data_cases']=counts
        result['preloaded_joint_data_accepted']=True
        result['pending'][0]='Reversible private review integration of the tested joint server and data package'
    if include_class_behavior:
        assert include_preloaded_data and include_live_forms
        from verify_combined_class_behavior import verify as verify_behavior
        behavior=verify_behavior(workspace)
        assert behavior['build_receipt_sha256']==receipt_hash
        result['joint_class_behavior_cases']=behavior['joint_class_behavior_cases']
        result['rendered_spell_visuals_accepted']=False
        evidence['joint_class_behavior']=digest(candidate/'verified_class_behavior.json')
    if include_private_review:
        assert include_preloaded_data
        review=workspace/'ExpansionRaceLab/MinotaurOwnerReview'
        install_path=review/'joint_integration.json'
        install=json.loads(install_path.read_text())
        assert all(install.get(k) for k in ['installed','review_only','all_existing_rows_preserved'])
        assert not any(install[k] for k in ['normal_installation_modified','review_database_replaced','race_class_activation_changed'])
        assert install['server_build_receipt_sha256']==receipt_hash and install['existing_tables_verified']>=126
        assert install['creation_scope']=='minotaur_only'
        assert len(install['installed_files'])==6
        for name,expected in install['installed_files'].items():
            path=Path(name).resolve();assert path.is_relative_to(review.resolve()) and digest(path)==expected
        smoke_path=workspace/'ExpansionRaceLab/CombinedExpansionReviewMigration/verified.json'
        smoke=json.loads(smoke_path.read_text())
        assert all(smoke.get(k) for k in ['passed','joint_server_installed','live_native_menu_passed',
                   'character_inventory_quest_task_tables_unchanged_after_live_menu'])
        assert len(smoke['tables_verified'])>=12 and not smoke['normal_installation_modified']
        evidence['private_review_installation']=digest(install_path)
        evidence['private_review_menu_and_progress']=digest(smoke_path)
        result['private_review_joint_server_and_data_installed']=True
        result['private_review_creation_scope']='minotaur_only'
        result['pending'][0]='Owner review and normal delivery; private review integration is complete'
    (candidate/'verified_joint_creation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--include-native-world',action='store_true')
    parser.add_argument('--include-advanced-protocol',action='store_true')
    parser.add_argument('--include-live-forms',action='store_true')
    parser.add_argument('--include-preloaded-data',action='store_true')
    parser.add_argument('--include-class-behavior',action='store_true')
    parser.add_argument('--include-private-review',action='store_true')
    args=parser.parse_args();print(json.dumps(verify(args.workspace,args.include_native_world,args.include_advanced_protocol,args.include_live_forms,args.include_preloaded_data,args.include_class_behavior,args.include_private_review)))
