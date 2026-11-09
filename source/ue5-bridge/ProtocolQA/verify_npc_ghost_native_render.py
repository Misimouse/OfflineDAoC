"""Render the candidate native controller at two actual original idle poses per model."""
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from prepare_combined_expansion_data import digest
from verify_stealth_render_native import png_rgb


def verify(workspace, engine):
    lab = workspace/'NpcVisualFlagsLab'
    build_path = lab/'native_build.json'
    build = json.loads(build_path.read_text())
    assert build['passed']
    project = Path(build['project'])
    binary = project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    normal = workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(binary) == build['binaries_sha256'][binary.name]
    assert digest(normal) == build['normal_binary_sha256']
    source = Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/path) == sha for path, sha in build['source_sha256'].items())
    materials = lab/'MaterialsCandidate/prepared.json'
    samples = lab/'samples_imported.json'
    inputs = {str(p): digest(p) for p in [build_path, binary, normal, materials, samples]}
    private = lab/'RenderHost/Plugins/DAoCVisualBridge/Content/GhostAppearance_v01'
    protected = {str(p): digest(p) for p in private.rglob('*.uasset')}
    out = lab/'NativeRenderedAcceptance'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True)
    args = [str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'), str(project),
            '/Engine/Maps/Entry', '-game', '-DaocBridge', '-DaocBridgeReadOnly',
            '-DaocBridgeCatalog='+str(workspace/'models.json'),
            '-DaocBridgeNpcGhostCapture='+str(out),
            '-DaocBridgeNpcGhostMaterials='+str(materials),
            '-DaocBridgeNpcGhostSamples='+str(samples),
            '-d3d11', '-RenderOffscreen', '-windowed', '-ResX=800', '-ResY=600',
            '-forceDisableDebugViewModes', '-unattended', '-nosound', '-nosplash',
            '-abslog='+str(out/'render.log')]
    for key, filename in [('DisplaySettings', 'display.ini'), ('InterfaceSettings', 'interface.ini'),
                          ('KeyConfiguration', 'keys.ini'), ('ControlsSettings', 'camera.json'),
                          ('AudioSettings', 'audio.ini')]:
        args.append('-DaocBridge'+key+'='+str(out/filename))
    with (out/'stdout.log').open('w') as log:
        process = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT,
                                 timeout=300, creationflags=subprocess.CREATE_NO_WINDOW)
    assert process.returncode == 0 and (out/'native.json').is_file(), str(out)
    data = json.loads((out/'native.json').read_text(encoding='utf-8-sig'))
    assert data['passed'] and data['captures'] == 16 and not data['failures'], data
    values = {}
    frames = {}
    for model in ['110', '307']:
        for pose in range(2):
            name = model+'_pose'+str(pose)
            images = {state: png_rgb(out/(name+'_'+state+'.png'))
                      for state in ['ordinary', 'ghost', 'restored', 'background']}
            assert all(size == (512, 768) for size, _ in images.values())
            pixels = {state: item[1] for state, item in images.items()}
            def difference(a, b):
                return sum(abs(x-y) for x, y in zip(pixels[a], pixels[b]))/len(pixels[a])
            row = dict(background_mean=sum(pixels['background'])/len(pixels['background']),
                       ordinary_signal=difference('ordinary', 'background'),
                       ghost_signal=difference('ghost', 'background'),
                       ghost_difference=difference('ghost', 'ordinary'),
                       restoration_error=difference('restored', 'ordinary'))
            values[name] = row
            frames[name] = pixels['ordinary']
    pose_differences = {model: sum(abs(a-b) for a, b in zip(frames[model+'_pose0'], frames[model+'_pose1']))/len(frames[model+'_pose0'])
                        for model in ['110', '307']}
    unchanged = all(digest(Path(p)) == sha for p, sha in {**protected, **inputs}.items())
    passed = unchanged and all(row['background_mean'] > 10 and row['ordinary_signal'] > 1
                               and row['ghost_signal'] > .2 and row['ghost_difference'] > .3
                               and row['restoration_error'] < 1 for row in values.values())
    data.update(passed=passed, measurements=values, pose_differences=pose_differences,
                source_inputs=inputs, protected_assets=protected, protected_files_unchanged=unchanged,
                owner_gameplay_accepted=False, images={str(p): digest(p) for p in out.glob('*.png')})
    (out/'verified.json').write_text(json.dumps(data, indent=2))
    assert passed, dict(output=str(out), measurements=values, unchanged=unchanged)
    return dict(passed=True, output=str(out), measurements=values, pose_differences=pose_differences)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(verify(options.workspace.resolve(), options.engine.resolve())))
