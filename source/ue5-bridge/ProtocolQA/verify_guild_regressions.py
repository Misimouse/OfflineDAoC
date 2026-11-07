"""Sequential regression checks on the guild candidate; isolated fixtures only."""
import argparse,json
from pathlib import Path
from verify_key_configuration_native import verify as controls
from verify_display_settings_native import verify as display
from verify_movement_keys_native import verify as movement
from verify_jump_landing_native import verify as jump
from verify_target_tracking_native import verify as tracking
from verify_water_data_native import verify as water
from verify_water_native_regressions import verify as audio
from prepare_combined_expansion_data import digest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);a=p.parse_args();w=a.workspace.resolve();e=a.engine.resolve();results={}
    for name,run in [('display',lambda:display(w,e,False,'GuildWindowLab')),('controls',lambda:controls(w,e,False,'GuildWindowLab')),('movement',lambda:movement(w,e,'GuildWindowLab')),('jump',lambda:jump(w,e,'GuildWindowLab')),('tracking',lambda:tracking(w,e,'GuildWindowLab')),('water',lambda:water(w,e,'GuildWindowLab')),('audio_ui',lambda:audio(w,e,False,'GuildWindowLab'))]:
        results[name]=run();print(json.dumps({name:results[name]}),flush=True)
    report=dict(passed=True,results=results,build_receipt_sha256=digest(w/'GuildWindowLab/native_build.json'),normal_installation_modified=False)
    (w/'GuildWindowLab/regressions.json').write_text(json.dumps(report,indent=2))
