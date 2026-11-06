"""Exercise exact proposed Shar policy in marked disposable server sessions."""
import argparse
import os
from pathlib import Path
import runpy
import sys

parser=argparse.ArgumentParser(description=__doc__)
for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
parser.add_argument('--mode',choices=['creation','vampiir','gm_transfer'],required=True)
args=parser.parse_args();workspace=args.workspace.resolve();repo=Path(__file__).resolve().parents[3]
os.environ['DAOC_INSTALL']=str(args.install.resolve());os.environ['DAOC_BRIDGE_QA_GODOT']=str(repo/'source/ue5-bridge/Godot')
sys.path.insert(0,str(workspace/'ProtocolQA'));import qa_runtime
assert qa_runtime.ROOT.resolve()==workspace
target=Path(__file__).with_name('verify_character_creation_matrix_real.py')
sys.argv=[str(target),'--server-source',str(repo/'source/server'),'--candidate-build',str(workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate'),
    '--combined-expansions','--combined-data',str(workspace/'Reports/combined_expansions/data_integration/proposal.json'),
    '--central-shar-activation',str(workspace/'ExpansionRaceLab/CentralDelivery/SharActivation/plan.json')]
if args.mode=='vampiir':sys.argv+=['--vampiir-candidate','--vampiir-shar']
else:sys.argv+=['--shar-candidate','--starter-equipment-repair']
if args.mode=='gm_transfer':sys.argv+=['--shar-gm-transfer']
runpy.run_path(str(target),run_name='__main__')
