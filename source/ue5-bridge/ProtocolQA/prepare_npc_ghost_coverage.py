"""Prepare private ghost variants for current original bodies and equipment; never install."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest


def prepare(workspace, engine):
    lab = workspace/'NpcVisualFlagsLab'
    out = lab/'FullMaterialsCandidate'
    out.mkdir(parents=True, exist_ok=True)
    content = lab/'RenderHost/Plugins/DAoCVisualBridge/Content'
    assert not (content/'GhostAppearance_v01').is_junction()
    catalog = lab/'models_candidate.json'
    stealth = workspace/'Client/Plugins/DAoCVisualBridge/Content/ClassicUI/stealth_materials.json'
    binary = workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    protected = {str(p): digest(p) for p in [catalog, stealth, binary, workspace/'models.json']}
    rows = json.loads(catalog.read_text())
    original_materials = json.loads(stealth.read_text())['materials']
    inputs = out/'coverage_inputs.json'
    inputs.write_text(json.dumps(dict(
        meshes=sorted({r['asset'] for r in rows.values() if r.get('asset') and r.get('type') != 'hidden'}),
        materials=sorted(original_materials)), indent=2))
    project = lab/'RenderHost/GhostRenderHost.uproject'
    source = Path(__file__).resolve().parents[1]

    def run(script, env, label, timeout):
        args = [str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'), str(project),
                '-run=pythonscript', '-script='+str(script), '-unattended', '-nop4',
                '-nosplash', '-nullrhi', '-forceDisableDebugViewModes',
                '-abslog='+str(out/(label+'.log'))]
        with (out/(label+'_stdout.log')).open('w') as log:
            result = subprocess.run(args, env=dict(os.environ, **env), stdout=log,
                                    stderr=subprocess.STDOUT, timeout=timeout,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode == 0, str(out/(label+'.log'))

    coverage = out/'coverage.json'
    run(source/'audit_stealth_material_coverage_unreal.py',
        dict(DAOC_STEALTH_COVERAGE_INPUTS=str(inputs), DAOC_STEALTH_COVERAGE_OUTPUT=str(coverage)),
        'coverage', 300)
    data = json.loads(coverage.read_text())
    assert data['passed'] and not data['missing_meshes']
    originals = {}
    for asset in data['materials']:
        package = asset.split('.')[0]
        if package.startswith('/DAoCVisualBridge/'):
            path = content/(package.removeprefix('/DAoCVisualBridge/')+'.uasset')
        else:
            assert package.startswith('/InterchangeAssets/gltf/'), asset
            path = engine/'Plugins/Interchange/Assets/Content'/(package.removeprefix('/InterchangeAssets/')+'.uasset')
        assert path.is_file(), asset
        originals[str(path)] = digest(path)
    run(Path(__file__).with_name('prepare_npc_ghost_materials_unreal.py'),
        dict(DAOC_NPC_GHOST_INPUTS=str(coverage), DAOC_NPC_GHOST_OUTPUT=str(out)),
        'materials', 1800)
    prepared = json.loads((out/'prepared.json').read_text())
    assert prepared['passed'] and prepared['originals_unchanged']
    assert set(data['materials']).issubset(prepared['materials'])
    assert all(digest(Path(p)) == h for p, h in {**protected, **originals}.items())
    proof = dict(passed=True, installed=False, meshes=data['meshes'],
                 source_materials=len(data['materials']), mappings=len(prepared['materials']),
                 originals_unchanged=True, protected=protected, original_assets=originals,
                 prepared_sha256=digest(out/'prepared.json'), library=prepared['library'])
    (out/'verified.json').write_text(json.dumps(proof, indent=2))
    return {k: v for k, v in proof.items() if k not in ['protected', 'original_assets']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(prepare(options.workspace.resolve(), options.engine.resolve())))
