"""Exact native-only keyboard turning delivery and immutable acceptance chain."""
from pathlib import Path
from npc_ghost_receipts import read
from prepare_combined_expansion_data import digest

NATIVE_TARGETS = ['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules'] + [
    'Source/DAoCVisualBridge/Private/'+name for name in ['DAoCBridgeSubsystem.cpp',
        'DAoCBridgeKeyConfiguration.cpp','DAoCBridgeKeyConfigurationAcceptance.cpp',
        'DAoCBridgeMovementKeysAcceptance.cpp','DAoCBridgeKeyboardTurning.h',
        'DAoCBridgeKeyboardTurningAcceptance.inl']]


def expected_files(workspace,proofs,verify_sources=True,successor_rows=None):
    from player_trade_receipts import predecessor_hash

    lab = workspace/'KeyboardTurningLab'
    build = read(lab/'native_build.json')
    old = read(workspace/'OriginalControlsLab/native_build.json')
    assert build['passed'] and build['normal_binary_sha256'] == old['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    native,math,tracking,ui,vitals = [read(Path(proofs[k])) for k in ['native','math','tracking','ui','vitals']]
    for proof in [native,math,tracking,ui,vitals]:
        assert proof['passed'] and proof['build_receipt_sha256'] == digest(lab/'native_build.json')
    assert native['checks'] >= 330 and not native['failures']
    assert math['checks'] == 108 and math['models'] == 13 and not math['failures']
    assert tracking['checks'] >= 35 and not tracking['failures']
    assert set(ui['reports']) == {'classic','player'} and all(r['passed'] and r['checks'] >= 68 for r in ui['reports'].values())
    assert vitals['checks'] >= 23 and not vitals['failures']
    catalog_rows = {key: row for key, row in (successor_rows or {}).items() if key == str(workspace/'models.json')}
    assert all(predecessor_hash(Path(p),catalog_rows) == sha for p,sha in vitals['source_inputs'].items())
    source = Path(__file__).resolve().parents[1]
    plugin = workspace/'Client/Plugins/DAoCVisualBridge'
    candidate = Path(build['project']).parent/'Plugins/DAoCVisualBridge'
    rows = []
    for relative in NATIVE_TARGETS:
        if relative.startswith('Source/'):
            key = str(Path(relative.removeprefix('Source/')))
            before,after = old['source_sha256'].get(key),build['source_sha256'][key]
            origin = source/'UnrealPlugin/DAoCVisualBridge'/relative
        else:
            before,after = old['binaries_sha256'][Path(relative).name],build['binaries_sha256'][Path(relative).name]
            origin = candidate/relative
        if verify_sources:
            assert origin.is_file() and digest(origin) == after,str(origin)
        target = plugin/relative
        assert target.resolve().is_relative_to(workspace.resolve())
        rows.append(dict(source=str(origin),target=str(target),before_sha256=before,after_sha256=after))
    assert len(rows) == len({r['target'] for r in rows}) == 8
    return rows


def verify(workspace,successor_rows=None):
    successor_rows = successor_rows or {}
    def current_hash(path):
        replacement = successor_rows.get(str(path))
        if replacement:
            assert digest(path) == replacement['after_sha256']
            return replacement['before_sha256']
        return digest(path)
    lab = workspace/'KeyboardTurningLab'
    path = lab/'installed.json'
    data = read(path) if path.exists() else None
    if not data or not data.get('installed'):
        return None,{}
    assert data['phase']=='complete' and not any(data[k] for k in ['database_modified','server_rules_modified','map_geometry_modified','teleport_enabled'])
    predecessor = workspace/'OriginalControlsLab/installed.json'
    assert digest(predecessor) == data['predecessor_receipt_sha256']
    assert read(predecessor)['native_after_sha256'] == data['native_before_sha256']
    assert data['evidence'] and all(digest(Path(p)) == sha for p,sha in data['evidence'].items())
    expected = {r['target']:r for r in expected_files(workspace,data['proofs'],verify_sources=False,successor_rows=successor_rows)}
    rows = {r['target']:r for r in data['files']}
    assert len(rows)==len(data['files'])==len(expected) and rows.keys()==expected.keys()
    for target,row in rows.items():
        assert all(row[k]==expected[target][k] for k in ['source','before_sha256','after_sha256'])
        assert current_hash(Path(target))==row['after_sha256']
    assert data['native_after_sha256']==read(lab/'native_build.json')['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    return data,rows
