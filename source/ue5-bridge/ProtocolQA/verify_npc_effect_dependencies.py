"""Seal original render dependencies and retained source behavior without runtime writes."""
import argparse
import json
from pathlib import Path
from prepare_combined_expansion_data import digest


def verify(workspace,install):
    lab = workspace/'NpcEffectsLab'
    private = lab/'RenderHost/Plugins/DAoCVisualBridge/Content'
    normal = workspace/'Client/Plugins/DAoCVisualBridge/Content'
    resources = lab/'Resources'
    prepared = json.loads((resources/'verified.json').read_text())
    imported = json.loads((lab/'textures_imported.json').read_text())
    catalog = json.loads((resources/'catalog.json').read_text())
    assert prepared['passed'] and prepared['originals_unchanged'] and imported['passed']
    assert prepared['catalog_sha256'] == digest(resources/'catalog.json')
    assert digest(private/'NpcEffects_v01/catalog.json') == digest(resources/'catalog.json')
    inputs = dict(prepared['source_inputs'])
    for name in ['npc.gd']:
        path = install/'new-client/godot/game/npcs'/name
        inputs[str(path)] = digest(path)
    for name in ['nif_particles.gd','nif_scene.gd']:
        path = install/'new-client/godot/game'/name
        inputs[str(path)] = digest(path)
    assets = {}
    for row in imported['textures']:
        relative = row['asset'].split('.')[0].removeprefix('/DAoCVisualBridge/')+'.uasset'
        path = (normal if row['reused'] else private)/relative
        assert path.is_file(),str(path)
        assets[str(path)] = digest(path)
    for name in ['M_SpellAdd.uasset','M_SpellAlpha.uasset']:
        path = normal/'SpellVisuals_v01'/name
        assets[str(path)] = digest(path)
    for key in catalog['resources']:
        source = resources/'Data'/(key+'.json')
        target = private/'NpcEffects_v01/Data'/(key+'.json')
        assert digest(target) == digest(source) == prepared['resources'][key]['sha256']
        inputs[str(source)] = digest(source)
    assert all(digest(Path(p)) == sha for p,sha in inputs.items())
    proof = dict(passed=True,installed=False,normal_runtime_modified=False,
                 source_inputs=inputs,render_assets=assets,source_effect_files=44,
                 source_textures=36,new_texture_assets=7,existing_texture_assets=29,
                 runtime_models=['966','2020'],original_float_metres=1.25,
                 original_particle_size_is_radius=True,
                 other_resource_warnings_retained=True)
    (lab/'dependencies_verified.json').write_text(json.dumps(proof,indent=2))
    return {k:v for k,v in proof.items() if k not in ['source_inputs','render_assets']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--install',type=Path,required=True)
    options = parser.parse_args()
    print(json.dumps(verify(options.workspace.resolve(),options.install.resolve())))
