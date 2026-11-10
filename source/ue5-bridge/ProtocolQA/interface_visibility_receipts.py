"""Verified interface visibility delivery through the existing command and chat UI."""
from pathlib import Path
from npc_ghost_receipts import read
from prepare_combined_expansion_data import digest
NATIVE_SOURCES=['Public/DAoCBridgeSubsystem.h']+['Private/'+n for n in ['DAoCBridgeChat.cpp','DAoCBridgeWorldPointer.cpp','DAoCBridgeClassicUI.cpp','DAoCBridgeInventory.cpp','DAoCBridgePlayerStatus.cpp','DAoCBridgeInterfaceSettings.h','DAoCBridgeInterfaceSettings.cpp','DAoCBridgeViewport.cpp','DAoCBridgeSubsystem.cpp','DAoCBridgeKeyConfiguration.cpp','DAoCBridgeKeyConfigurationAcceptance.cpp','DAoCBridgeInterfaceVisibilityAcceptance.inl']]

def inventory(workspace):
    lab=workspace/'InterfaceVisibilityLab';build=read(lab/'native_build.json');plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    source=Path(__file__).resolve().parents[1];candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge';rows=[]
    for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor.modules']:
        rows.append((candidate/'Binaries/Win64'/name,plugin/'Binaries/Win64'/name,build['binaries_sha256'][name]))
    for relative in NATIVE_SOURCES:
        key=str(Path('DAoCVisualBridge')/relative);rows.append((source/'UnrealPlugin/DAoCVisualBridge/Source'/key,plugin/'Source'/key,build['source_sha256'][key]))
    assert len(rows)==15 and len({str(r[1]) for r in rows})==15
    return rows

def expected_files(workspace,proofs,verify_sources=True):
    lab=workspace/'InterfaceVisibilityLab';build=read(lab/'native_build.json');base=read(lab/'runtime_baseline.json')
    old=read(workspace/'ChatReplyLab/installed.json');assert build['passed'] and build['normal_binary_sha256']==old['native_after_sha256']==base['normal_binary_sha256']
    native=read(Path(proofs['native']))
    assert native['passed'] and native['checks']>=453 and not native['failures']
    assert native['build_receipt_sha256']==digest(lab/'native_build.json')
    if verify_sources:
        source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source';assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    rows=[]
    for origin,target,after in inventory(workspace):
        assert target.resolve().is_relative_to(workspace.resolve())
        if verify_sources:assert origin.is_file() and digest(origin)==after,str(origin)
        rows.append(dict(source=str(origin),target=str(target),before_sha256=base['files'][str(target)],after_sha256=after))
    assert {r['target'] for r in rows}==set(base['files'])
    return rows

def verify(workspace,successor_rows=None):
    successor_rows=successor_rows or {}
    def current_hash(path):
        replacement=successor_rows.get(str(path))
        if replacement:
            assert digest(path)==replacement["after_sha256"]
            return replacement["before_sha256"]
        return digest(path)
    lab=workspace/'InterfaceVisibilityLab';path=lab/'installed.json';data=read(path) if path.exists() else None
    if not data or not data.get('installed'):return None,{}
    assert data['phase']=='complete' and not any(data[k] for k in ['database_modified','server_rules_modified','map_geometry_modified','teleport_enabled'])
    predecessor=workspace/'ChatReplyLab/installed.json';assert digest(predecessor)==data['predecessor_receipt_sha256'] and read(predecessor)['native_after_sha256']==data['native_before_sha256']
    assert data['evidence'] and all(digest(Path(p))==h for p,h in data['evidence'].items())
    expected={r['target']:r for r in expected_files(workspace,data['proofs'],False)};rows={r['target']:r for r in data['files']}
    assert len(rows)==len(data['files'])==15 and rows.keys()==expected.keys()
    for target,row in rows.items():
        assert all(row[k]==expected[target][k] for k in ['source','before_sha256','after_sha256'])
        assert current_hash(Path(target))==row['after_sha256']
    assert data['native_after_sha256']==read(lab/'native_build.json')['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    return data,rows
