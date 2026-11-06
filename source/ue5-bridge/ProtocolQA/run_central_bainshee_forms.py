"""Verify all three original Bainshee form cycles with installed central native assets."""
import argparse
import os
from pathlib import Path
import runpy
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace', type=Path, required=True)
parser.add_argument('--install', type=Path, required=True)
parser.add_argument('--race', type=int, choices=[9, 11, 12])
args = parser.parse_args()
workspace, install = args.workspace.resolve(), args.install.resolve()
repo = Path(__file__).resolve().parents[3]
if args.race is None:
    output = workspace/'Reports/central_bainshee_forms'
    output.mkdir(exist_ok=True)
    for race in [9, 11, 12]:
        with (output/('race_'+str(race)+'.log')).open('w', encoding='utf-8') as log:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--workspace', str(workspace),
                                     '--install', str(install), '--race', str(race)], stdout=log, stderr=subprocess.STDOUT)
        print('Installed central Bainshee form race '+str(race)+': '+('passed' if result.returncode == 0 else 'FAILED'), flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
else:
    os.environ['DAOC_INSTALL'] = str(install)
    os.environ['DAOC_BRIDGE_QA_GODOT'] = str(repo/'source/ue5-bridge/Godot')
    sys.path.insert(0, str(workspace/'ProtocolQA'))
    import qa_runtime
    assert qa_runtime.ROOT.resolve() == workspace
    target = Path(__file__).with_name('verify_starting_spells_real.py')
    sys.argv = [str(target), '--class-id', '39', '--level', '5', '--bainshee-proposal',
                str(workspace/'Reports/appearance/bainshee_probe_proposal.json'), '--server-source',
                str(repo/'source/server'), '--candidate-build', str(workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate'),
                '--combined-expansions', '--combined-data', str(workspace/'Reports/combined_expansions/data_integration/proposal.json'),
                '--bainshee-form-cycle', '--bainshee-race', str(args.race), '--native-form-probe', '--central-installed-native']
    runpy.run_path(str(target), run_name='__main__')
