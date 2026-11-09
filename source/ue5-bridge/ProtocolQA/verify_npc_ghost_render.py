"""Run bounded private captures and reject blank images or incomplete restoration.

This checks the render fixture, not gameplay acceptance or complete NPC coverage.
"""
import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

from prepare_combined_expansion_data import digest
from verify_stealth_render_native import png_rgb


def measurements(output):
    result = {}
    for model in ['110', '307', '110_90', '110_180', '110_270', '307_90', '307_180', '307_270']:
        images = {name: png_rgb(output / (model + '_' + name + '.png'))
                  for name in ['ordinary', 'ghost', 'restored', 'background']}
        assert all(size == (512, 768) for size, _ in images.values())
        pixels = {name: data[1] for name, data in images.items()}

        def difference(a, b):
            return sum(abs(x-y) for x, y in zip(pixels[a], pixels[b])) / len(pixels[a])

        row = dict(background_mean=sum(pixels['background'])/len(pixels['background']), ordinary_signal=difference('ordinary', 'background'),
                   ghost_signal=difference('ghost', 'background'),
                   ghost_difference=difference('ghost', 'ordinary'),
                   restoration_error=difference('restored', 'ordinary'),
                   ordinary_peak=max(pixels['ordinary']),
                   ghost_peak=max(pixels['ghost']))
        result[model] = row
    return result


def verify(workspace, engine):
    lab = workspace / 'NpcVisualFlagsLab'
    project = lab / 'RenderHost/GhostRenderHost.uproject'
    config = project.parent/'Config/DefaultEngine.ini'
    # ShaderCore.cpp documents value 2 as disabling editor-only diagnostic modes.
    # Require it in this private host rather than changing the installed project.
    assert 'r.ForceDebugViewModes=2' in config.read_text(), 'Private capture host must disable diagnostic view permutations'
    private = project.parent / 'Plugins/DAoCVisualBridge/Content/GhostAppearance_v01'
    assert private.resolve().is_relative_to(project.parent.resolve())
    protected = [workspace / 'models.json',
                 workspace / 'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll']
    protected += list((private / 'Samples').rglob('*.uasset'))
    before = {str(p): digest(p) for p in protected}
    script = Path(__file__).with_name('render_npc_ghost_samples_unreal.py')
    inputs = {str(p): digest(p) for p in [script, config, lab/'samples_imported.json', lab/'MaterialsCandidate/prepared.json']}
    out = lab/'RenderedAcceptance'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True)
    env = dict(os.environ, DAOC_NPC_GHOST_LAB=str(lab), DAOC_NPC_GHOST_RENDER_OUTPUT=str(out))
    args = [str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'), str(project),
            '-run=pythonscript', '-script='+str(script), '-unattended', '-nop4',
            '-nosplash', '-d3d11', '-RenderOffscreen', '-AllowCommandletRendering',
            '-forceDisableDebugViewModes',
            '-abslog='+str(out/'render.log')]
    with (out/'stdout.log').open('w') as log:
        process = subprocess.run(args, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 timeout=900, creationflags=subprocess.CREATE_NO_WINDOW)
    assert process.returncode == 0, str(out)
    capture = json.loads((out/'capture_result.json').read_text())
    assert capture['passed'] and not capture['errors'] and not capture['installed']
    values = measurements(out)
    report = dict(passed=False, installed=False, owner_gameplay_accepted=False,
                  front_surface_validated=False, measurements=values, inputs=inputs,
                  protected_files=before, images={str(p): digest(p) for p in out.glob('*.png')})
    assert all(digest(Path(p)) == h for p, h in before.items()), 'Protected source changed'
    assert all(digest(Path(p)) == h for p, h in inputs.items()), 'Inputs changed during capture'
    report['protected_files_unchanged'] = True
    report['passed'] = all(row['background_mean'] > 10 and row['ordinary_signal'] > 1 and row['ghost_signal'] > .2
                          and row['ghost_difference'] > .3 and row['restoration_error'] < 1
                          for row in values.values())
    (out/'verified.json').write_text(json.dumps(report, indent=2))
    assert report['passed'], values
    return dict(passed=True, installed=False, output=str(out), measurements=values)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(verify(options.workspace.resolve(), options.engine.resolve())))
