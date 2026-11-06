"""Test the proposed central Bainshee/Vampiir eligibility policy in disposable sessions."""
import argparse
import os
from pathlib import Path
import runpy
import subprocess
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace',type=Path,required=True)
parser.add_argument('--install',type=Path,required=True)
parser.add_argument('--class-name',choices=['bainshee','vampiir'])
args=parser.parse_args()
workspace,install=args.workspace.resolve(),args.install.resolve()
repo=Path(__file__).resolve().parents[3]
if args.class_name is None:
    output=workspace/'Reports/central_spellclass_activation'
    output.mkdir(exist_ok=True)
    for name in ['bainshee','vampiir']:
        with (output/(name+'.log')).open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--workspace',str(workspace),
                '--install',str(install),'--class-name',name],stdout=log,stderr=subprocess.STDOUT)
        print('Central '+name+' creation/reentry: '+('passed' if result.returncode==0 else 'FAILED'),flush=True)
        if result.returncode:raise SystemExit(result.returncode)
else:
    os.environ['DAOC_INSTALL']=str(install)
    os.environ['DAOC_BRIDGE_QA_GODOT']=str(repo/'source/ue5-bridge/Godot')
    sys.path.insert(0,str(workspace/'ProtocolQA'))
    import qa_runtime
    assert qa_runtime.ROOT.resolve()==workspace
    target=Path(__file__).with_name('verify_character_creation_matrix_real.py')
    sys.argv=[str(target),'--'+args.class_name+'-candidate','--server-source',str(repo/'source/server'),
        '--candidate-build',str(workspace/'ExpansionRaceLab/CombinedExpansionServerCandidate'),
        '--combined-expansions','--combined-data',str(workspace/'Reports/combined_expansions/data_integration/proposal.json'),
        '--central-spellclass-activation',str(workspace/'ExpansionRaceLab/CentralDelivery/SpellClassActivation/plan.json')]
    runpy.run_path(str(target),run_name='__main__')
