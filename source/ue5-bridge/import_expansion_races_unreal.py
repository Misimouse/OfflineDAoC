"""Import original expansion figures only in their isolated private asset host."""
import hashlib
import json
import os
import re
import struct
import traceback
from pathlib import Path
import unreal

lab = Path(os.environ['DAOC_EXPANSION_RACE_LAB']).resolve()
project = Path(unreal.Paths.project_dir()).resolve()
assert project == lab / 'NativeHost', 'Expansion imports require the separate private host'
content = (project / 'Plugins/DAoCVisualBridge/Content').resolve()
assert content.is_relative_to(lab), 'Never import through an installed/shared content junction'
report = {'passed': False, 'installed': False, 'models': {}, 'errors': []}
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()
normalize = lambda value: re.sub(r'[^a-z0-9]', '', str(value).lower())
try:
    sources = lab / 'SourceFigures'
    verification = json.loads((lab / 'figure_exports_verified.json').read_text())
    assert verification['passed'] and not verification['installed']
    rows = json.loads((sources / 'exported.json').read_text())
    catalogue = {}
    for row in rows:
        ident = str(row['id'])
        file = Path(row['file']).resolve()
        assert file.is_relative_to(sources)
        raw = file.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        assert sha == verification['models'][ident]['sha256']
        size = struct.unpack_from('<I', raw, 12)[0]
        document = json.loads(raw[20:20+size])
        expected = [animation['name'] for animation in document['animations']]
        destination = '/DAoCVisualBridge/ExpansionRaces_v01/Model_' + ident + '_' + sha[:12]
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
        loaded = [assets.load_asset(path) for path in paths]
        meshes = [asset for asset in loaded if isinstance(asset, unreal.SkeletalMesh)]
        animations = [asset for asset in loaded if isinstance(asset, unreal.AnimSequence)]
        assert len(meshes) == 1, (ident, 'expected one original skeletal mesh')
        skeleton = meshes[0].get_editor_property('skeleton')
        clips = {}
        for name in expected:
            names = {normalize(name), normalize('model_' + ident + name)}
            matches = [animation for animation in animations if normalize(animation.get_name()) in names]
            if name == 'RESET' and not matches:
                continue
            assert len(matches) == 1, (ident, name, 'missing or ambiguous imported clip')
            animation = matches[0]
            assert animation.get_editor_property('skeleton') == skeleton
            clips[name] = animation.get_path_name()
        catalogue[ident] = {'asset': meshes[0].get_path_name(), 'type': 'skeletal', 'scale': row['scale'],
                            'yaw_offset': -90, 'name': row['name'], **clips}
        report['models'][ident] = {'source_sha256': sha, 'mesh': meshes[0].get_path_name(),
                                   'skeleton': skeleton.get_path_name(), 'imported_clips': len(clips),
                                   'source_clips': len(expected), 'creation_accepted': False}
    assert set(catalogue) == {'1075', '1087', '1419'}
    (lab / 'models_expansion_candidate.json').write_text(json.dumps(catalogue, indent=2), encoding='utf-8')
    report['passed'] = True
except Exception:
    report['errors'].append(traceback.format_exc())
(lab / 'native_import.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
assert report['passed'], report['errors']
