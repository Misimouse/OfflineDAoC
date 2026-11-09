"""Run the disposable NPC protocol test with explicit local installation paths."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def verify(workspace, install, engine):
    source = Path(__file__).resolve().parent
    prepared = json.loads((workspace/'Reports/protocol_qa/prepared.json').read_text())
    assert Path(prepared['root']).resolve().is_relative_to((workspace/'ProtocolQA').resolve())
    assert (install/'runtime/server/GameServer.dll').is_file()
    assert (workspace/'ProtocolQA/qa_runtime.py').is_file() and (workspace/'bridge_paths.py').is_file()
    target = workspace/'ProtocolQA/verify_npc_ghost_real.py'
    shutil.copy2(source/'verify_npc_ghost_real.py', target)
    env = dict(os.environ, DAOC_INSTALL=str(install), DAOC_UE_ENGINE=str(engine),
               DAOC_BRIDGE_SOURCE_QA=str(source))
    lab = workspace/'NpcVisualFlagsLab'
    with (lab/'real_protocol_stdout.log').open('w') as log:
        result = subprocess.run([sys.executable, str(target)], env=env, cwd=workspace,
                                stdout=log, stderr=subprocess.STDOUT, timeout=600,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0, str(lab/'real_protocol_stdout.log')
    proof = sorted((lab/'RealProtocol').glob('*/verified.json'))[-1]
    data = json.loads(proof.read_text())
    assert data['passed'] and data['database_restored'] and data['normal_runtime_unchanged']
    assert data['normal_shutdown'] and not data['errors'] and all(data['checks'].values())
    return dict(passed=True, checks=len(data['checks']), real_protocol=True,
                normal_runtime_unchanged=True, private_database_restored=True, proof=str(proof))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['workspace', 'install', 'engine']:
        parser.add_argument('--'+name, type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(verify(options.workspace.resolve(), options.install.resolve(), options.engine.resolve())))
