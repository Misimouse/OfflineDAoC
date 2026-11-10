"""Verified item shortcuts delivery through the existing command and chat UI."""
from pathlib import Path
from npc_ghost_receipts import read
from prepare_combined_expansion_data import digest
NATIVE_SOURCES=['Private/'+n for n in ['DAoCBridgeClassicUI.cpp','DAoCBridgeKeyConfiguration.cpp','DAoCBridgeKeyConfigurationAcceptance.cpp','DAoCBridgeItemShortcuts.h','DAoCBridgeItemShortcutsAcceptance.inl']]

def inventory(workspace):
    lab=workspace/'ItemShortcutsLab';build=read(lab/'native_build.json');plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    source=Path(__file__).resolve().parents[1];candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge';rows=[]
    for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor.modules']:
        rows.append((candidate/'Binaries/Win64'/name,plugin/'Binaries/Win64'/name,build['binaries_sha256'][name]))
    for relative in NATIVE_SOURCES:
        key=str(Path('DAoCVisualBridge')/relative);rows.append((source/'UnrealPlugin/DAoCVisualBridge/Source'/key,plugin/'Source'/key,build['source_sha256'][key]))
    assert len(rows)==7 and len({str(r[1]) for r in rows})==7
    return rows

def expected_files(workspace,proofs,verify_sources=True):
    lab=workspace/'ItemShortcutsLab';build=read(lab/'native_build.json');base=read(lab/'runtime_baseline.json')
    old=read(workspace/'InterfaceVisibilityLab/installed.json');assert build['passed'] and build['normal_binary_sha256']==old['native_after_sha256']==base['normal_binary_sha256']
    native=read(Path(proofs['native']))
    assert native['passed'] and native['checks']>=507 and not native['failures']
    assert native['build_receipt_sha256']==digest(lab/'native_build.json')
    state,merchant,consumable=[read(Path(proofs[k])) for k in ['state','merchant','consumable']]
    assert state['passed'] and {r['test']:r['checks'] for r in state['reports']}=={'test_inventory.gd':35,'test_inventory_denial.gd':23,'test_classic_ui.gd':43,'test_consumable_details.gd':12}
    for proof in [merchant,consumable]:
        assert proof['passed'] and proof['real_protocol'] and proof['disposable_only'] and all(proof['checks'].values()) and proof['normal_shutdown'] and proof['normal_runtime_unchanged'] and proof['database_restored']
    assert len(merchant['checks'])>=13 and len(consumable['checks'])>=11
    if verify_sources:
        for proof in [state,merchant,consumable]:assert all(digest(Path(p))==h for p,h in proof['source_inputs'].items())
        source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source';assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    rows=[]
    for origin,target,after in inventory(workspace):
        assert target.resolve().is_relative_to(workspace.resolve())
        if verify_sources:assert origin.is_file() and digest(origin)==after,str(origin)
        rows.append(dict(source=str(origin),target=str(target),before_sha256=base['files'][str(target)],after_sha256=after))
    assert {r['target'] for r in rows}==set(base['files'])
    return rows

def verify(workspace):
    lab=workspace/'ItemShortcutsLab';path=lab/'installed.json';data=read(path) if path.exists() else None
    if not data or not data.get('installed'):return None,{}
    assert data['phase']=='complete' and not any(data[k] for k in ['database_modified','server_rules_modified','map_geometry_modified','teleport_enabled'])
    predecessor=workspace/'InterfaceVisibilityLab/installed.json';assert digest(predecessor)==data['predecessor_receipt_sha256'] and read(predecessor)['native_after_sha256']==data['native_before_sha256']
    assert data['evidence'] and all(digest(Path(p))==h for p,h in data['evidence'].items())
    expected={r['target']:r for r in expected_files(workspace,data['proofs'],False)};rows={r['target']:r for r in data['files']}
    assert len(rows)==len(data['files'])==7 and rows.keys()==expected.keys()
    for target,row in rows.items():
        assert all(row[k]==expected[target][k] for k in ['source','before_sha256','after_sha256'])
        assert digest(Path(target))==row['after_sha256']
    assert data['native_after_sha256']==read(lab/'native_build.json')['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    return data,rows
