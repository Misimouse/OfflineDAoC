"""Extract original NPC effect resources privately, reusing the existing effect extractor."""
import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path
import shutil
import struct
from prepare_combined_expansion_data import digest


def prepare(workspace, install):
    lab = workspace/'NpcEffectsLab'
    out = lab/'Resources'
    (out/'Data').mkdir(parents=True,exist_ok=True)
    original = install/'new-client/godot'
    monsters = original/'content/monsters/monsters.json'
    source = Path(__file__).resolve().parents[1]/'export_spell_visuals.py'
    normal = workspace/'models.json'
    binary = workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    protected = {str(p):digest(p) for p in [monsters,source,normal,binary]}
    textures = {}
    (lab/'SourceSpellVisuals_v01/Textures').mkdir(parents=True,exist_ok=True)
    # Reuse only the trusted extractor functions. Its top-level spell export/install
    # statements must never execute while preparing this independent candidate.
    tree = ast.parse(source.read_text())
    functions = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['texture','extract']]
    assert len(functions) == 2
    scope = dict(Path=Path,json=json,struct=struct,base64=base64,hashlib=hashlib,shutil=shutil,
                 R=lab,textures=textures,formats={5120:'b',5121:'B',5122:'h',5123:'H',5125:'I',5126:'f'},
                 widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16})
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),scope)
    definitions = json.loads(monsters.read_text(encoding='utf-8-sig'))
    current = json.loads(normal.read_text())
    existing = json.loads((workspace/'Client/Plugins/DAoCVisualBridge/Content/SpellVisuals_v01/catalog.json').read_text())
    catalog = dict(version=1,models={},textures={},resources={})
    audit = dict(passed=False,installed=False,source_inputs=protected,errors=[],resources={},
                 source_models_with_effects=0,effect_only_models=0,current_effect_models=[])
    for model, info in definitions.items():
        effects = info.get('effects',[])
        if not effects:
            continue
        only = not info.get('gltf') and not info.get('race')
        entry = dict(effect_only=only,scale=info.get('scale',1),float_units=info.get('float_units',[]),effects=[])
        audit['source_models_with_effects'] += 1
        audit['effect_only_models'] += int(only)
        if model in current:
            audit['current_effect_models'].append(model)
        for effect in effects:
            relative = effect['gltf'].removeprefix('res://')
            path = (original/relative).resolve()
            assert path.is_relative_to((original/'content/monsters/effects').resolve())
            protected[str(path)] = digest(path)
            for texture_path in path.parent.glob('textures/**/*.png'):
                protected[str(texture_path)] = digest(texture_path)
            key = hashlib.sha256(effect['gltf'].encode()).hexdigest()[:16]
            if key not in catalog['resources']:
                data = scope['extract'](path)
                target = out/'Data'/(key+'.json')
                target.write_text(json.dumps(data,separators=(',',':')))
                gltf = json.loads(path.read_text())
                parents = {child:i for i,node in enumerate(gltf.get('nodes',[])) for child in node.get('children',[])}
                inherited = []
                for index,node in enumerate(gltf.get('nodes',[])):
                    if 'mesh' not in node:
                        continue
                    ancestor = parents.get(index)
                    while ancestor is not None:
                        value = gltf['nodes'][ancestor]
                        if any(k in value for k in ['matrix','translation','rotation','scale']):
                            inherited.append(index)
                            break
                        ancestor = parents.get(ancestor)
                modes = sorted({str(p['material'].get('billboard','')) for p in data['parts']})
                audit['resources'][key] = dict(source=str(path),parts=len(data['parts']),
                    emitters=len(data['particles']),billboards=modes,meshes_with_parent_transforms=inherited,
                    warnings=gltf.get('extras',{}).get('warnings',[]),sha256=digest(target))
                catalog['resources'][key] = key
            entry['effects'].append(dict(data=key,node=effect.get('attach',''),
                range_m=effect.get('range_m',0),autoscale=effect.get('autoscale',False),nif=effect['nif']))
        catalog['models'][model] = entry
    imports = {}
    for key,path in textures.items():
        catalog['textures'][key] = existing.get('textures',{}).get(key,
            '/DAoCVisualBridge/NpcEffects_v01/Textures/T_'+key+'.T_'+key)
        if key not in existing.get('textures',{}):
            imports[key] = path
    assert all(digest(Path(p)) == sha for p,sha in protected.items())
    assert catalog['models']['966']['effect_only'] and catalog['models']['966']['float_units'] == [50.,50.]
    assert catalog['models']['966']['effects'][0]['range_m'] == 60.
    assert catalog['models']['2020']['effect_only']
    for key in catalog['resources']:
        data = json.loads((out/'Data'/(key+'.json')).read_text())
        assert data['parts'] or data['particles'], key
        for part in data['parts']:
            assert all(isinstance(i,int) and 0 <= i < len(part['positions']) for i in part['indices'])
    (out/'catalog.json').write_text(json.dumps(catalog,indent=2))
    (out/'textures_to_import.json').write_text(json.dumps(imports,indent=2))
    audit.update(passed=True,originals_unchanged=True,resource_count=len(catalog['resources']),
                 textures=len(textures),new_texture_imports=len(imports),
                 reused_texture_assets=len(textures)-len(imports),catalog_sha256=digest(out/'catalog.json'))
    (out/'verified.json').write_text(json.dumps(audit,indent=2))
    return {k:v for k,v in audit.items() if k not in ['source_inputs','resources']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--install',type=Path,required=True)
    options = parser.parse_args()
    print(json.dumps(prepare(options.workspace.resolve(),options.install.resolve())))
