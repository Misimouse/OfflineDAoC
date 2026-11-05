"""Import verified expansion outfits in the private host; never activate a race."""
import hashlib
import json
import os
from pathlib import Path
import re
import traceback
import unreal

lab = Path(os.environ['DAOC_EXPANSION_RACE_LAB']).resolve()
package = Path(os.environ.get('DAOC_EXPANSION_RACE_PACKAGE',str(lab))).resolve()
assert package.is_relative_to(lab)
project = Path(unreal.Paths.project_dir()).resolve()
assert project == lab / 'NativeHost'
content = (project / 'Plugins/DAoCVisualBridge/Content').resolve()
assert content.is_relative_to(lab), 'Never import through shared content junctions'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
normalize = lambda name: re.sub(r'[^a-z0-9]', '', str(name).lower())
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()
report = {'passed': False, 'installed': False, 'races': {}, 'errors': [], 'race_activation': False,
          'pending': ['Armour texture/material catalogue', 'Native outfit/helmet/cloak rendering and motion acceptance', 'Server race rules and transport']}
try:
    verified = read(package / 'outfit_exports_verified.json')
    assert verified['passed'] and not verified['installed']
    sources = read(package / 'SourceCosmetics/exported.json')
    source_races = {r['race'] for r in sources}
    assert source_races == set(verified['races'])
    assert source_races in ({'sha_m', 'sha_f'}, {'mino'})
    models = read(package / 'models_expansion_candidate.json')
    definitions = {}
    for row in sources:
        race, ident = row['race'], str(row['base_id'])
        file = Path(row['file']).resolve()
        assert file.is_relative_to(package / 'SourceCosmetics')
        sha = hashlib.sha256(file.read_bytes()).hexdigest()
        assert sha == verified['races'][race]['sha256']
        destination = '/DAoCVisualBridge/ExpansionOutfits_v01/' + race + '_' + sha[:12]
        paths = assets.list_assets(destination, recursive=True, include_folder=False)
        if not paths:
            task = unreal.AssetImportTask()
            task.filename = str(file)
            task.destination_path = destination
            task.automated = True
            task.save = True
            task.replace_existing = False
            tools.import_asset_tasks([task])
            paths = assets.list_assets(destination, recursive=True, include_folder=False)
        meshes = [assets.load_asset(p) for p in paths if 'SkeletalMesh' in str(assets.find_asset_data(p).asset_class_path)]
        meshes = [m for m in meshes if isinstance(m, unreal.SkeletalMesh)]
        assert len(meshes) == 1
        mesh = meshes[0]
        original = unreal.load_asset(models[ident]['asset'])
        assert isinstance(original, unreal.SkeletalMesh)
        before, after = unreal.SkeletonModifier(), unreal.SkeletonModifier()
        assert before.set_skeletal_mesh(original) and after.set_skeletal_mesh(mesh)
        old_bones = {normalize(n): n for n in before.get_all_bone_names()}
        new_bones = {normalize(n): n for n in after.get_all_bone_names()}
        common = old_bones.keys() & new_bones.keys()
        original_bip = {name for name in old_bones if name.startswith('bip01')}
        assert original_bip <= common and len(original_bip) >= 100
        for name in common:
            a = before.get_bone_transform(old_bones[name], True)
            b = after.get_bone_transform(new_bones[name], True)
            assert a.translation.distance(b.translation) < .1, ('Bind position changed', race, name)
            assert a.scale3d.distance(b.scale3d) < .001, ('Bind scale changed', race, name)
            assert abs(sum(getattr(a.rotation, k) * getattr(b.rotation, k) for k in ['x', 'y', 'z', 'w'])) > .99999, ('Bind rotation changed', race, name)
        skeleton = mesh.get_editor_property('skeleton')
        skeleton.add_compatible_skeleton(original.get_editor_property('skeleton'))
        assert assets.save_loaded_asset(skeleton)
        descriptors = {s['material']: s for s in row['sections']}
        sections = []
        for index, material in enumerate(mesh.get_editor_property('materials')):
            name = str(material.material_slot_name)
            assert name in descriptors
            sections.append(dict(descriptors[name], index=index))
        assert len(sections) == len(descriptors) == verified['races'][race]['sections']
        if package==lab:assert len(sections)==31
        definition = {'asset': mesh.get_path_name(), 'skeleton': skeleton.get_path_name(), 'base_id': ident,
                      'original_asset': original.get_path_name(), 'gender': 'f' if race.endswith('_f') else 'm',
                      'sections': sections, 'clothes': row['clothes'], 'variants': row['variants'], 'cloaks': row['cloaks'], 'source_sha256': sha}
        definitions[mesh.get_path_name()] = definition
        models[ident]['asset'] = mesh.get_path_name()
        report['races'][race] = {'asset': mesh.get_path_name(), 'sections': len(sections), 'verified_common_bones': len(common),
                                 'source_only_bones': sorted(old_bones.keys() - common), 'outfit_only_bones': sorted(new_bones.keys() - common), 'source_sha256': sha}
    (package / 'outfit_definitions_candidate.json').write_text(json.dumps(definitions, indent=2), encoding='utf-8')
    (package / 'models_outfits_candidate.json').write_text(json.dumps(models, indent=2), encoding='utf-8')
    report['passed'] = True
except Exception:
    report['errors'].append(traceback.format_exc())
(package / 'native_outfit_import.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
assert report['passed'], report['errors']
