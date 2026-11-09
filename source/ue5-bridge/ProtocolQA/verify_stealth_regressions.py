"""Check the uninstalled stealth successor without writing predecessor evidence."""
import argparse,json
from pathlib import Path
from prepare_combined_expansion_data import digest
from verify_compass_native import verify as compass
from verify_world_clock_native import verify as clock
from verify_player_vitals_native import verify as vitals
from verify_ui_scale_native import verify as scale
from verify_window_recovery_native import verify as windows
from verify_item_handover_native import verify as handover
from verify_hover_details_native import verify as hover
from verify_emblem_picker_native import verify as emblem
from verify_guild_native import verify as guild
from verify_display_settings_native import verify as display
from verify_key_configuration_native import verify as controls
from verify_movement_keys_native import verify as movement
from verify_jump_landing_native import verify as jump
from verify_target_tracking_native import verify as tracking
from verify_water_data_native import verify as water
from verify_water_native_regressions import verify as audio

LAB='StealthLab'
def verify(workspace,engine):
    root=workspace/LAB;assert root.is_dir() and not (root/'installed.json').exists()
    progress=root/'regression_progress.json'
    previous=json.loads(progress.read_text()) if progress.exists() else {}
    results=previous.get('results',{}) if previous.get('build_receipt_sha256')==digest(root/'native_build.json') else {}
    cases=[('windows',lambda:windows(workspace,engine,False,LAB)),('scale',lambda:scale(workspace,engine,False,LAB)),('hover',lambda:hover(workspace,engine,False,LAB)),('handover',lambda:handover(workspace,engine,False,LAB)),('emblem',lambda:emblem(workspace,engine,False,LAB)),('guild',lambda:guild(workspace,engine,False,LAB)),('display',lambda:display(workspace,engine,False,LAB)),('controls',lambda:controls(workspace,engine,False,LAB)),('movement',lambda:movement(workspace,engine,LAB)),('jump',lambda:jump(workspace,engine,LAB)),('tracking',lambda:tracking(workspace,engine,LAB)),('water',lambda:water(workspace,engine,LAB)),('audio_ui',lambda:audio(workspace,engine,False,LAB))]
    fixtures=[p for p in sorted((workspace/'PlayerVitalsLab/RealProtocol').glob('*/initial_snapshot.json')) if (p.parent/'real_protocol.json').exists() and json.loads((p.parent/'real_protocol.json').read_text(encoding='utf-8')).get('passed')]
    assert fixtures,'Verified real 1 HP fixture required'
    cases.append(('player_vitals',lambda:vitals(workspace,engine,fixtures[-1],False,LAB)))
    cases.append(('compass',lambda:compass(workspace,engine,False,LAB)))
    cases.append(('world_clock',lambda:clock(workspace,engine,False,LAB)))
    for name,run in cases:
        if name in results:
            proof=Path(results[name]['output'])/'verified.json';data=json.loads(proof.read_text(encoding='utf-8-sig'))
            assert data['passed'] and data['build_receipt_sha256']==digest(root/'native_build.json')
            continue
        results[name]=run()
        progress.write_text(json.dumps(dict(build_receipt_sha256=digest(root/'native_build.json'),results=results),indent=2),encoding='utf-8')
        print(json.dumps({name:results[name]}),flush=True)
    result=dict(passed=True,results=results,build_receipt_sha256=digest(root/'native_build.json'),normal_installation_modified=False)
    (root/'regressions.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return dict(passed=True,packages=len(results))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve())))
