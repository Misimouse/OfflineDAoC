"""Seven-file native group targeting successor; existing transport remains unchanged."""
from pathlib import Path
from npc_ghost_receipts import read
from prepare_combined_expansion_data import digest
NATIVE_TARGETS=['Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll','Binaries/Win64/UnrealEditor.modules']+[
    'Source/DAoCVisualBridge/Private/'+n for n in ['DAoCBridgeClassicUI.cpp','DAoCBridgeKeyConfiguration.cpp',
        'DAoCBridgeKeyConfigurationAcceptance.cpp','DAoCBridgeGroupTargeting.h','DAoCBridgeGroupTargetingAcceptance.inl']]


def expected_files(workspace,proofs,verify_sources=True):
    lab=workspace/'GroupTargetKeysLab';build=read(lab/'native_build.json');old=read(workspace/'KeyboardTurningLab/native_build.json')
    assert build['passed'] and build['normal_binary_sha256']==old['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    native,party=[read(Path(proofs[k])) for k in ['native','party']]
    assert native['passed'] and native['checks']>=396 and not native['failures']
    assert party['passed'] and party['state_checks']>=43 and party['native_checks']>=79 and not party['server_started']
    assert all(p['build_receipt_sha256']==digest(lab/'native_build.json') for p in [native,party])
    if verify_sources:assert all(digest(Path(p))==sha for p,sha in party['source_inputs'].items())
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge';plugin=workspace/'Client/Plugins/DAoCVisualBridge';candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge';rows=[]
    for relative in NATIVE_TARGETS:
        if relative.startswith('Source/'):
            key=str(Path(relative.removeprefix('Source/')));before,after=old['source_sha256'].get(key),build['source_sha256'][key];origin=source/relative
        else:before,after=old['binaries_sha256'][Path(relative).name],build['binaries_sha256'][Path(relative).name];origin=candidate/relative
        if verify_sources:assert origin.is_file() and digest(origin)==after,str(origin)
        target=plugin/relative;assert target.resolve().is_relative_to(workspace.resolve())
        rows.append(dict(source=str(origin),target=str(target),before_sha256=before,after_sha256=after))
    assert len(rows)==len({r['target'] for r in rows})==7
    return rows


def verify(workspace):
    lab=workspace/'GroupTargetKeysLab';path=lab/'installed.json';data=read(path) if path.exists() else None
    if not data or not data.get('installed'):return None,{}
    assert data['phase']=='complete' and not any(data[k] for k in ['database_modified','server_rules_modified','map_geometry_modified','teleport_enabled'])
    predecessor=workspace/'KeyboardTurningLab/installed.json';assert digest(predecessor)==data['predecessor_receipt_sha256']
    assert read(predecessor)['native_after_sha256']==data['native_before_sha256']
    assert data['evidence'] and all(digest(Path(p))==sha for p,sha in data['evidence'].items())
    expected={r['target']:r for r in expected_files(workspace,data['proofs'],verify_sources=False)};rows={r['target']:r for r in data['files']}
    assert len(rows)==len(data['files'])==len(expected) and rows.keys()==expected.keys()
    for target,row in rows.items():
        assert all(row[k]==expected[target][k] for k in ['source','before_sha256','after_sha256'])
        assert digest(Path(target))==row['after_sha256']
    assert data['native_after_sha256']==read(lab/'native_build.json')['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    return data,rows
