"""Check the uninstalled handover successor without writing predecessor evidence."""
import argparse,json
from pathlib import Path
from prepare_combined_expansion_data import digest
from verify_item_handover_native import verify as handover
from verify_emblem_picker_native import verify as emblem
from verify_guild_native import verify as guild
from verify_display_settings_native import verify as display
from verify_key_configuration_native import verify as controls
from verify_movement_keys_native import verify as movement
from verify_jump_landing_native import verify as jump
from verify_target_tracking_native import verify as tracking
from verify_water_data_native import verify as water
from verify_water_native_regressions import verify as audio

LAB='ItemHandoverLab'
def verify(workspace,engine):
    root=workspace/LAB;assert root.is_dir() and not (root/'installed.json').exists()
    results={}
    cases=[('handover',lambda:handover(workspace,engine)),('emblem',lambda:emblem(workspace,engine,False,LAB)),('guild',lambda:guild(workspace,engine,False,LAB)),('display',lambda:display(workspace,engine,False,LAB)),('controls',lambda:controls(workspace,engine,False,LAB)),('movement',lambda:movement(workspace,engine,LAB)),('jump',lambda:jump(workspace,engine,LAB)),('tracking',lambda:tracking(workspace,engine,LAB)),('water',lambda:water(workspace,engine,LAB)),('audio_ui',lambda:audio(workspace,engine,False,LAB))]
    for name,run in cases:
        results[name]=run();print(json.dumps({name:results[name]}),flush=True)
    result=dict(passed=True,results=results,build_receipt_sha256=digest(root/'native_build.json'),normal_installation_modified=False)
    (root/'regressions.json').write_text(json.dumps(result,indent=2));return dict(passed=True,packages=len(results))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve())))
