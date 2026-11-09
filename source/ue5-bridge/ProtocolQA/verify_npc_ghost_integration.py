"""Replay verified original-server NPC rows through normal native entity creation/presentation."""
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest


def verify(workspace, engine, materials=None):
    lab = workspace/'NpcVisualFlagsLab'
    materials = materials or lab/'MaterialsCandidate/prepared.json'
    build_path = lab/'native_build.json'
    build = json.loads(build_path.read_text())
    assert build['passed']
    source = Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/path) == sha for path, sha in build['source_sha256'].items())
    proof = next(p for p in reversed(sorted((lab/'RealProtocol').glob('*/verified.json')))
                 if json.loads(p.read_text())['passed'])
    protocol = json.loads(proof.read_text())
    assert protocol['normal_runtime_unchanged'] and protocol['database_restored'] and len(protocol['checks']) >= 28
    snapshot = proof.parent/'npc_snapshot.json'
    catalog_proof = lab/'catalog_verified.json'
    catalog_data = json.loads(catalog_proof.read_text())
    catalog = Path(catalog_data['catalog'])
    assert catalog_data['passed'] and digest(catalog) == catalog_data['sha256']
    normal = workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(normal) == build['normal_binary_sha256']
    inputs = {str(p): digest(p) for p in [build_path, proof, snapshot, catalog_proof, catalog,
                                         materials, normal]}
    out = lab/'NativeIntegration'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True)
    report = out/'native.json'
    args = [str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'), build['project'],
            '/Engine/Maps/Entry', '-game', '-DaocBridge', '-DaocBridgeReadOnly',
            '-DaocBridgeCatalog='+str(catalog), '-DaocBridgeNpcGhostIntegrationTest='+str(report),
            '-DaocBridgeNpcGhostMaterials='+str(materials),
            '-DaocBridgeNpcGhostSnapshot='+str(snapshot), '-nullrhi', '-unattended',
            '-nosound', '-nosplash', '-abslog='+str(out/'native.log')]
    for key, filename in [('DisplaySettings', 'display.ini'), ('InterfaceSettings', 'interface.ini'),
                          ('KeyConfiguration', 'keys.ini'), ('ControlsSettings', 'camera.json'),
                          ('AudioSettings', 'audio.ini')]:
        args.append('-DaocBridge'+key+'='+str(out/filename))
    with (out/'stdout.log').open('w') as log:
        process = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT,
                                 timeout=180, creationflags=subprocess.CREATE_NO_WINDOW)
    assert process.returncode == 0 and report.is_file(), str(out)
    data = json.loads(report.read_text(encoding='utf-8-sig'))
    assert data['passed'] and data['checks'] >= 21 and not data['failures'], data
    assert all(digest(Path(p)) == sha for p, sha in inputs.items())
    data.update(source_inputs=inputs, replayed_real_server_rows=True,
                live_native_connection=False, installed=False, normal_runtime_unchanged=True)
    (out/'verified.json').write_text(json.dumps(data, indent=2))
    return dict(passed=True, checks=data['checks'], output=str(out), installed=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--materials', type=Path)
    options = parser.parse_args()
    print(json.dumps(verify(options.workspace.resolve(), options.engine.resolve(), options.materials)))
