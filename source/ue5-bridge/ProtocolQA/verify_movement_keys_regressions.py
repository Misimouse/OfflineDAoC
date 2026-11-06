"""Run existing audio/UI regressions against the private movement-keys candidate."""
import argparse,json
from pathlib import Path
from verify_water_native_regressions import verify
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--installed',action='store_true');a=p.parse_args()
    print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.installed,'MovementKeysLab')))
