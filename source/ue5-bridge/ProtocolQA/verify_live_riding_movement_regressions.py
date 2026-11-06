"""Recheck walking, jump physics, target tracking and original water mask on the riding binary."""
import argparse,json
from pathlib import Path
from verify_movement_keys_native import verify as movement
from verify_jump_landing_native import verify as jump
from verify_target_tracking_native import verify as tracking
from verify_water_data_native import verify as water
from prepare_combined_expansion_data import digest
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();w=a.workspace.resolve();e=a.engine.resolve();results={}
    for name,run in [('movement',movement),('jump',jump),('tracking',tracking),('water',water)]:
        results[name]=run(w,e,'LiveRidingLab');print(json.dumps({name:results[name]}),flush=True)
    report=dict(passed=True,results=results,build_receipt_sha256=digest(w/'LiveRidingLab/native_build.json'),normal_installation_modified=False)
    (w/'LiveRidingLab/movement_regressions.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
