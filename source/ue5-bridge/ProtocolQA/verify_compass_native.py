"""Verify original compass art, heading and window behaviour in a private native viewport."""
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from prepare_combined_expansion_data import digest
from verify_options_audio_native import read


def verify(workspace, engine, installed=False):
    root = workspace / 'CompassLab'
    bp = root / 'native_build.json'
    build = read(bp)
    assert build['passed']
    source = Path(__file__).resolve().parents[1] / 'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source / p) == h for p, h in build['source_sha256'].items())
    normal = workspace / 'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    expected = build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256']
    assert digest(normal) == expected
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['compass_installed']
    original = root / 'Art/compass_bar.png'
    art_hash = '29c5db6f8795c82cc38c675c108f0c8663020dfb6ce1677f3201f6af4b3dad37'
    assert digest(original) == art_hash
    out = root / ('InstalledCompassAcceptance' if installed else 'CompassAcceptance') / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True)
    report = out / 'compass.json'
    fixture = out / 'fixture.json'
    fixture.write_bytes((workspace / 'Reports/vault/fixture.json').read_bytes())
    project = str(workspace / 'Client/DAoCBridgeClient.uproject') if installed else build['project']
    args = [str(engine / 'Binaries/Win64/UnrealEditor-Cmd.exe'), project, '/Engine/Maps/Entry',
            '-game', '-DaocBridge', '-DaocBridgeReadOnly', '-DaocBridgeCompassTest=' + str(report),
            '-DaocBridgeCompassFixture=' + str(fixture),
            '-DaocBridgeEquipmentCatalog=' + str(workspace / 'equipment_catalog_v01.json')]
    if not installed:
        args.append('-DaocBridgeCompassArt=' + str(original))
    for key, name in [('DisplaySettings', 'display.ini'), ('InterfaceSettings', 'interface.ini'),
                      ('KeyConfiguration', 'keys.ini'), ('ControlsSettings', 'camera.json'), ('AudioSettings', 'audio.ini')]:
        args.append('-DaocBridge' + key + '=' + str(out / name))
    args += ['-nosound', '-unattended', '-nosplash', '-d3d11', '-RenderOffscreen', '-windowed',
             '-ResX=1280', '-ResY=720', '-abslog=' + str(out / 'engine.log')]
    inputs = {str(p): digest(p) for p in [fixture, original]}
    with (out / 'stdout.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, timeout=360,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0 and report.exists(), str(out)
    data = read(report)
    assert data['passed'] and not data['failures'] and data['checks'] >= 24, data
    assert digest(normal) == expected and all(digest(Path(p)) == h for p, h in inputs.items())
    assert all(digest(source / p) == h for p, h in build['source_sha256'].items())
    data.update(build_receipt_sha256=digest(bp), source_inputs=inputs,
                normal_installation_modified=False, original_art_sha256=art_hash)
    proof = out / 'verified.json'
    proof.write_text(json.dumps(data, indent=2), encoding='utf-8')
    (root / ('installed_compass_acceptance.json' if installed else 'compass_acceptance.json')).write_text(
        json.dumps(dict(passed=True, proof=str(proof), proof_sha256=digest(proof)), indent=2), encoding='utf-8')
    return dict(passed=True, checks=data['checks'], output=str(out))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['workspace', 'engine']:
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--installed', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(), args.engine.resolve(), args.installed)))
