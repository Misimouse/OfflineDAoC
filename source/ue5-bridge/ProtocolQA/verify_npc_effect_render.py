"""Render original NPC effect bodies at four camera views and two original timeline samples."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest
from verify_stealth_render_native import png_rgb


def verify(workspace,engine,installed=False):
    lab = workspace/'NpcEffectsLab'
    build_path = lab/'native_build.json'
    build = json.loads(build_path.read_text())
    source = Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert build['passed'] and all(digest(source/p) == sha for p,sha in build['source_sha256'].items())
    project = workspace/'Client/DAoCBridgeClient.uproject' if installed else Path(build['project'])
    binary = project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(binary) == build['binaries_sha256'][binary.name]
    normal = workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64'/binary.name
    assert digest(normal) == (build['binaries_sha256'][normal.name] if installed else build['normal_binary_sha256'])
    catalog = workspace/'models.json' if installed else lab/'models_candidate.json'
    private = (workspace/'Client' if installed else lab/'RenderHost')/'Plugins/DAoCVisualBridge/Content/NpcEffects_v01'
    protected = {str(p):digest(p) for p in private.rglob('*') if p.is_file()}
    protected.update({str(p):digest(p) for p in [normal,binary,build_path,catalog]})
    out = lab/('InstalledRenderedAcceptance' if installed else 'RenderedAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True)
    args = [str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry',
            '-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeCatalog='+str(catalog),
            '-DaocBridgeNpcEffectsCapture='+str(out),'-d3d11','-RenderOffscreen','-windowed',
            '-ResX=800','-ResY=600','-forceDisableDebugViewModes','-unattended','-nosound',
            '-nosplash','-abslog='+str(out/'render.log')]
    for key,filename in [('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),
                         ('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:
        args.append('-DaocBridge'+key+'='+str(out/filename))
    with (out/'stdout.log').open('w') as log:
        process = subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=300,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
    assert process.returncode == 0 and (out/'native.json').is_file(),str(out)
    data = json.loads((out/'native.json').read_text(encoding='utf-8-sig'))
    assert data['passed'] and data['captures'] == 32,data
    metrics,frames = {},{}
    for model in ['966','2020']:
        for view in range(4):
            for time in range(2):
                key = f'{model}_view{view}_time{time}'
                effect = png_rgb(out/(key+'_effect.png'))
                background = png_rgb(out/(key+'_background.png'))
                assert effect[0] == background[0] == (512,512)
                differences = [abs(a-b) for a,b in zip(effect[1],background[1])]
                metrics[key] = dict(background_mean=sum(background[1])/len(background[1]),
                    effect_signal=sum(differences)/len(differences),changed_channels=sum(x>10 for x in differences))
                frames[key] = effect[1]
    animation = {f'{model}_view{view}':sum(abs(a-b) for a,b in zip(frames[f'{model}_view{view}_time0'],frames[f'{model}_view{view}_time1']))/len(frames[f'{model}_view{view}_time0'])
                 for model in ['966','2020'] for view in range(4)}
    unchanged = all(digest(Path(p)) == sha for p,sha in protected.items())
    passed = unchanged and all(r['background_mean']>10 and r['effect_signal']>.001 and r['changed_channels']>10 for r in metrics.values())
    passed = passed and all(value>.001 for value in animation.values())
    data.update(passed=passed,installed=installed,metrics=metrics,animation_differences=animation,
                protected_files=protected,protected_files_unchanged=unchanged,
                owner_gameplay_accepted=False,visual_review_required=True,
                images={str(p):digest(p) for p in out.glob('*.png')})
    (out/'verified.json').write_text(json.dumps(data,indent=2))
    assert passed,dict(output=str(out),metrics=metrics,animation=animation,unchanged=unchanged)
    return dict(passed=True,output=str(out),metrics=metrics,animation_differences=animation)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--engine',type=Path,required=True)
    parser.add_argument('--installed',action='store_true')
    options = parser.parse_args()
    print(json.dumps(verify(options.workspace.resolve(),options.engine.resolve(),options.installed)))
