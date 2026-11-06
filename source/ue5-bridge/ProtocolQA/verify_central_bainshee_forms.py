"""Seal live Bainshee form evidence against current installed central native inputs."""
import argparse
import json
from pathlib import Path

from prepare_combined_expansion_data import digest


def verify(workspace):
    output = workspace/'Reports/central_bainshee_forms'
    models = json.loads((workspace/'models.json').read_text())
    accepted = []
    for race, model in [(9,1883),(11,1885),(12,1884)]:
        folder = output/('race_'+str(race))
        path = folder/'real_protocol.json'
        row = json.loads(path.read_text())
        assert all(row.get(k) for k in ['passed','complete','database_restored','candidate_server_restored',
                   'normal_shutdown','native_uses_installed_central_assets'])
        assert not row['errors'] and row['race']==race and row['form_model']==model
        assert row['native_observer_exit']==0 and 25<=row['form_timer_seconds']<=40
        assert all(row['checks'][k] for k in ['positive_buff_retains_original_form',
                   'live_native_body_and_portrait_transform','original_offensive_cast_transforms',
                   'original_timer_restores_appearance_and_inventory',
                   'live_native_original_body_and_equipment_restored','native_form_inputs_unchanged'])
        assert all(digest(Path(p))==sha for p,sha in row['native_form_inputs'].items())
        stages = {stage:json.loads((folder/('native_'+stage+'.json')).read_text())['player_visual']
                  for stage in ['before','transformed','restored']}
        before, changed, restored = (stages[k] for k in ['before','transformed','restored'])
        assert changed['model_id']==model and changed['body_asset']==models[str(model)]['asset']
        assert changed['portrait_asset']==changed['body_asset'] and changed['body_visible'] and changed['weapon_components']==0
        assert before['body_asset']==restored['body_asset'] and before['portrait_asset']==restored['portrait_asset']
        assert before['weapon_components']==restored['weapon_components'] and restored['body_visible']
        captures = sorted(folder.glob('visual_stage_*.png'))
        assert len(captures)==3 and all(p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') for p in captures)
        accepted.append({'race':race,'form_model':model,'report_sha256':digest(path),
                         'native_inputs':row['native_form_inputs'],'captures':{str(p):digest(p) for p in captures}})
    result = {'passed':True,'installed_native_inputs_verified':True,'cases':accepted,
              'normal_class_activation_included':False,'normal_database_modified':False,
              'owner_visual_acceptance':False,'combat_damage_acceptance':False,'spell_effect_audio_acceptance':False}
    (output/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return {'passed':True,'races':[r['race'] for r in accepted],'current_installed_native_verified':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve())))
