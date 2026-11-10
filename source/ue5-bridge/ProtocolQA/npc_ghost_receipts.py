"""Exact NPC ghost successor: original protocol, private art, and predecessor integrity."""
import json
from pathlib import Path
from prepare_combined_expansion_data import digest

NATIVE_TARGETS = ['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll', 'Binaries/Win64/UnrealEditor.modules',
                  'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h'] + [
    'Source/DAoCVisualBridge/Private/'+name for name in [
        'DAoCBridgeSubsystem.cpp', 'DAoCBridgeGhostMaterials.cpp', 'DAoCBridgeGhostMaterials.h',
        'DAoCBridgeGhostMaterialAcceptance.cpp', 'DAoCBridgeGhostMaterialVisual.cpp',
        'DAoCBridgeNpcGhostPresentation.cpp', 'DAoCBridgeNpcGhostIntegrationAcceptance.cpp']]
GODOT_TARGETS = ['decoded_world_adapter.gd', 'npc_visual_flags.gd']


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def expected_files(workspace, proofs):
    lab = workspace/'NpcVisualFlagsLab'
    build = read(lab/'native_build.json')
    old = read(workspace/'PersonalTorchLab/native_build.json')
    native = read(Path(proofs['native']))
    integration = read(Path(proofs['integration']))
    render = read(Path(proofs['render']))
    real = read(Path(proofs['real']))
    coverage = read(lab/'FullMaterialsCandidate/verified.json')
    materials = lab/'FullMaterialsCandidate/prepared.json'
    prepared = read(materials)
    catalog = read(lab/'catalog_verified.json')
    state = read(lab/'state_tests.json')
    assert build['passed'] and build['normal_binary_sha256'] == old['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    assert state['passed'] and state['checks'] >= 1815
    assert all(digest(Path(p)) == h for p, h in state['source_inputs'].items())
    assert native['passed'] and native['build_sha256'] == digest(lab/'native_build.json')
    assert {r['name']:r['checks'] for r in native['reports']} == dict(ghost=48, torch=19, pose=55, combat=25, motion=387)
    assert native['material_sha256'] == digest(materials)
    for row in native['reports']:
        assert read(Path(row['report']))['passed'] and digest(Path(row['report'])) == row['sha256']
    assert integration['passed'] and integration['checks'] >= 21 and integration['replayed_real_server_rows'] and not integration['live_native_connection']
    assert render['passed'] and render['captures'] == 16 and render['protected_files_unchanged']
    assert real['passed'] and len(real['checks']) >= 28 and all(real['checks'].values())
    assert real['normal_shutdown'] and real['database_restored'] and real['normal_runtime_unchanged']
    assert coverage['passed'] and coverage['originals_unchanged'] and coverage['mappings'] >= 3006
    assert coverage['prepared_sha256'] == digest(materials) and prepared['passed'] and prepared['originals_unchanged']
    assert catalog['passed'] and catalog['originals_unchanged'] and digest(Path(catalog['catalog'])) == catalog['sha256']
    source = Path(__file__).resolve().parents[1]
    plugin = workspace/'Client/Plugins/DAoCVisualBridge'
    candidate = Path(build['project']).parent/'Plugins/DAoCVisualBridge'
    rows = []

    def add(origin, target, before, after):
        assert origin.is_file() and digest(origin) == after, str(origin)
        assert target.resolve().is_relative_to(workspace.resolve()), str(target)
        rows.append(dict(source=str(origin), target=str(target), before_sha256=before, after_sha256=after))

    for relative in NATIVE_TARGETS:
        key = str(Path(relative.removeprefix('Source/')))
        if relative.startswith('Source/'):
            before, after = old['source_sha256'].get(key), build['source_sha256'][key]
            origin = source/'UnrealPlugin/DAoCVisualBridge'/relative
        else:
            before, after = old['binaries_sha256'][Path(relative).name], build['binaries_sha256'][Path(relative).name]
            origin = candidate/relative
        add(origin, plugin/relative, before, after)
    previous = read(workspace/'RemotePlayerLab/installed.json')
    before_godot = {r['target']:r['after_sha256'] for r in previous['files']}
    for name in GODOT_TARGETS:
        origin = source/'Godot'/name
        add(origin, workspace/'Godot'/name, before_godot.get(str(workspace/'Godot'/name)), real['source_inputs'][str(origin)])
    add(Path(catalog['catalog']), workspace/'models.json', catalog['sources'][str(workspace/'models.json')], catalog['sha256'])
    runtime = lab/'npc_ghost_materials.json'
    expected = {k:prepared[k] for k in ['passed','installed','originals_unchanged','library','materials']}
    expected.update(version=1, source_manifest_sha256=digest(materials))
    assert read(runtime) == expected
    add(runtime, plugin/'Content/ClassicUI/npc_ghost_materials.json', None, digest(runtime))
    content = lab/'RenderHost/Plugins/DAoCVisualBridge/Content'
    library = prepared['library'].removeprefix('/DAoCVisualBridge/')
    assert library.startswith('GhostAppearance_v01/Materials/') and '..' not in library
    assets = sorted((content/library).rglob('*.uasset')) + sorted((content/'GhostAppearance_v01/Samples').rglob('*.uasset'))
    assert len(assets) >= 3035
    for asset in assets:
        add(asset, plugin/'Content'/asset.relative_to(content), None, render['protected_assets'][str(asset)])
    assert len({r['target'] for r in rows}) == len(rows)
    return rows


def verify(workspace):
    path = workspace/'NpcVisualFlagsLab/installed.json'
    data = read(path) if path.exists() else None
    if not data or not data.get('installed'):
        return None, {}
    assert data['phase'] == 'complete' and not any(data[k] for k in ['database_modified','server_rules_modified','map_geometry_modified','teleport_enabled'])
    predecessor = workspace/'PersonalTorchLab/installed.json'
    assert digest(predecessor) == data['predecessor_receipt_sha256']
    assert read(predecessor)['native_after_sha256'] == data['native_before_sha256']
    assert data['evidence'] and all(digest(Path(p)) == h for p, h in data['evidence'].items())
    expected = {r['target']:r for r in expected_files(workspace, data['proofs'])}
    rows = {r['target']:r for r in data['files']}
    assert len(rows) == len(data['files']) == len(expected) and rows.keys() == expected.keys()
    for target, row in rows.items():
        assert all(row[k] == expected[target][k] for k in ['source','before_sha256','after_sha256'])
        assert digest(Path(target)) == row['after_sha256']
    assert data['native_after_sha256'] == read(workspace/'NpcVisualFlagsLab/native_build.json')['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    return data, rows
