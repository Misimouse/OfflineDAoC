"""Sealed original NPC effect-body delivery, independent of world population."""
from pathlib import Path
from npc_ghost_receipts import read
from prepare_combined_expansion_data import digest

NATIVE_TARGETS = ['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll', 'Binaries/Win64/UnrealEditor.modules'] + [
    'Source/DAoCVisualBridge/Private/'+name for name in [
        'DAoCBridgeSubsystem.cpp', 'DAoCBridgeSpellVisuals.cpp', 'DAoCBridgeInteraction.cpp',
        'DAoCBridgeNameplates.cpp', 'DAoCBridgeNpcEffectBody.h', 'DAoCBridgeNpcEffects.inl',
        'DAoCBridgeNpcEffectAcceptance.inl', 'DAoCBridgeNpcEffectVisual.inl']]


def expected_files(workspace, proofs, verify_sources=True):
    lab = workspace/'NpcEffectsLab'
    build = read(lab/'native_build.json')
    old = read(workspace/'NpcVisualFlagsLab/native_build.json')
    native, render = read(Path(proofs['native'])), read(Path(proofs['render']))
    dependencies = read(lab/'dependencies_verified.json')
    catalog = read(lab/'catalog_verified.json')
    assert build['passed'] and build['normal_binary_sha256'] == old['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    assert native['passed'] and native['build_sha256'] == digest(lab/'native_build.json')
    assert {r['name']:r['checks'] for r in native['reports']} == dict(npc=31,spell=30,ghost=48,torch=19,pose=55,combat=25,motion=387)
    for row in native['reports']:
        assert digest(Path(row['report'])) == row['sha256'] and read(Path(row['report']))['passed']
    assert render['passed'] and render['captures'] == 32 and render['protected_files_unchanged']
    assert all(digest(Path(p)) == sha for p,sha in render['images'].items())
    assert read(Path(proofs['render']).with_name('visual_review.json'))['reviewed']
    assert dependencies['passed'] and dependencies['runtime_models'] == ['966','2020']
    assert all(digest(Path(p)) == sha for p,sha in dependencies['render_assets'].items())
    if verify_sources:
        assert all(digest(Path(p)) == sha for p,sha in dependencies['source_inputs'].items())
    assert catalog['passed'] and catalog['changed_models'] == ['2020','966'] and catalog['models'] == 78
    assert digest(Path(catalog['candidate'])) == catalog['sha256'] == native['catalog_sha256']
    plugin = workspace/'Client/Plugins/DAoCVisualBridge'
    source = Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge'
    candidate = Path(build['project']).parent/'Plugins/DAoCVisualBridge'
    rows = []

    def add(origin,target,before,after):
        if verify_sources:
            assert origin.is_file() and digest(origin) == after,str(origin)
        assert target.resolve().is_relative_to(workspace.resolve()),str(target)
        rows.append(dict(source=str(origin),target=str(target),before_sha256=before,after_sha256=after))

    for relative in NATIVE_TARGETS:
        if relative.startswith('Source/'):
            key = str(Path(relative.removeprefix('Source/')))
            before,after = old['source_sha256'].get(key),build['source_sha256'][key]
            origin = source/relative
        else:
            before,after = old['binaries_sha256'][Path(relative).name],build['binaries_sha256'][Path(relative).name]
            origin = candidate/relative
        add(origin,plugin/relative,before,after)
    add(Path(catalog['candidate']),workspace/'models.json',catalog['before_catalogue_sha256'],catalog['sha256'])
    content = lab/'RenderHost/Plugins/DAoCVisualBridge/Content'
    assets = sorted(p for p in (content/'NpcEffects_v01').rglob('*') if p.is_file())
    assert len(assets) == 52
    for asset in assets:
        add(asset,plugin/'Content'/asset.relative_to(content),None,render['protected_files'][str(asset)])
    assert len(rows) == len({r['target'] for r in rows}) == 63
    return rows


def verify(workspace):
    lab = workspace/'NpcEffectsLab'
    path = lab/'installed.json'
    data = read(path) if path.exists() else None
    if not data or not data.get('installed'):
        return None,{}
    assert data['phase'] == 'complete' and not any(data[k] for k in ['database_modified','server_rules_modified','map_geometry_modified','teleport_enabled'])
    predecessor = workspace/'NpcVisualFlagsLab/installed.json'
    assert digest(predecessor) == data['predecessor_receipt_sha256']
    assert read(predecessor)['native_after_sha256'] == data['native_before_sha256']
    assert data['evidence'] and all(digest(Path(p)) == sha for p,sha in data['evidence'].items())
    expected = {r['target']:r for r in expected_files(workspace,data['proofs'],verify_sources=False)}
    rows = {r['target']:r for r in data['files']}
    assert len(rows) == len(data['files']) == len(expected) and rows.keys() == expected.keys()
    for target,row in rows.items():
        assert all(row[k] == expected[target][k] for k in ['source','before_sha256','after_sha256'])
        assert digest(Path(target)) == row['after_sha256']
    build = read(lab/'native_build.json')
    assert data['native_after_sha256'] == build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    return data,rows
