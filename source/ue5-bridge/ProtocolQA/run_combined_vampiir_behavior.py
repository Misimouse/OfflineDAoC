"""Exercise original Vampiir behavior with the complete private joint data package."""
import argparse
import os
from pathlib import Path
import runpy
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace', type=Path, required=True)
parser.add_argument('--install', type=Path, required=True)
parser.add_argument('--mode', choices=['power', 'buff', 'bolt'], required=True)
parser.add_argument('--combat-audio-native-candidate',action='store_true')
args = parser.parse_args()
assert not args.combat_audio_native_candidate or args.mode=='power'
workspace = args.workspace.resolve()
repo = Path(__file__).resolve().parents[3]
assert (workspace/'ProtocolQA/qa_runtime.py').is_file()
os.environ['DAOC_INSTALL'] = str(args.install.resolve())
os.environ['DAOC_BRIDGE_QA_GODOT'] = str(repo/'source/ue5-bridge/Godot')
sys.path.insert(0, str(workspace/'ProtocolQA'))
import qa_runtime
assert qa_runtime.ROOT.resolve() == workspace
target = Path(__file__).with_name('verify_starting_spells_real.py')
sys.argv = [str(target), '--class-id', '58', '--level', '50',
            '--expansion-proposal', str(workspace/'Reports/appearance/vampiir_probe_proposal.json'),
            '--career-proposal', str(workspace/'Reports/appearance/career_58_proposal.json'),
            '--server-source', str(repo/'source/server'), '--candidate-build',
            str(workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate'),
            '--combined-expansions', '--combined-data',
            str(workspace/'Reports/combined_expansions/data_integration/proposal.json')]
sys.argv += {'power': ['--expansion-power'], 'buff': ['--expansion-training', '--expansion-self-buff'],
             'bolt': ['--vampiir-bolt']}[args.mode]
if args.combat_audio_native_candidate:sys.argv.append('--combat-audio-native-candidate')
runpy.run_path(str(target), run_name='__main__')
