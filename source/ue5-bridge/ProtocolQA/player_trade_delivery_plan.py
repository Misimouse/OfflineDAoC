"""Build an exact, reviewable player-trade delivery manifest; never install files."""
import argparse,json
from pathlib import Path
from prepare_combined_expansion_data import digest

NATIVE=["Private/"+n for n in ["DAoCBridgeClassicUI.cpp","DAoCBridgeExchange.inl","DAoCBridgeItemHandover.cpp","DAoCBridgeItemHandoverAcceptance.cpp","DAoCBridgePlayerTrade.inl","DAoCBridgePlayerTradeAcceptance.cpp","DAoCBridgeSubsystem.cpp","DAoCBridgeViewport.cpp","DAoCBridgeWorldPointer.cpp"]]+["Public/DAoCBridgeSubsystem.h"]
GODOT=['live_gateway.gd','visual_bridge.gd','player_trade_state.gd','player_trade_controller.gd']

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def inventory(workspace,install,wire_proof):
    repo=Path(__file__).resolve().parents[3];source=repo/'source/ue5-bridge';root=workspace/'PlayerTradeGatewayLab';build=read(root/'native_build.json');candidate=Path(build['project']).parent/'Plugins/DAoCVisualBridge';normal=workspace/'Client/Plugins/DAoCVisualBridge'
    backend=Path(read(wire_proof)['candidate_backend']).parent;game=install/'new-client/godot';net=game/'game/net';producer=repo/'source/new-client/godot/game/net'
    pairs=[(candidate/'Binaries/Win64'/n,normal/'Binaries/Win64'/n) for n in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor.modules']]
    pairs += [(source/'UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge'/n,normal/'Source/DAoCVisualBridge'/n) for n in NATIVE]
    pairs += [(source/'Godot'/n,workspace/'Godot'/n) for n in GODOT]
    pairs += [(backend/n,game/'.godot/mono/temp/bin/Debug'/n) for n in ['MMOEngine.dll','MMOEngine.pdb']]
    core=backend.parent/'BackendSource/game/net/DaocClient.cs'
    pairs += [(core,net/'DaocClient.cs'),(core,producer/'DaocClient.cs'),(producer/'DaocTradeCodec.cs',net/'DaocTradeCodec.cs')]
    pairs += [(workspace/'PlayerTradeUILab/Content/ClassicUI/trade.png',normal/'Content/ClassicUI/trade.png')]
    return pairs

def validate(workspace,install,plan,after=False):
    assert plan['phase']=='prepared' and not any(plan[k] for k in ['database_modified','server_rules_modified','map_modified','normal_installation_modified'])
    root=workspace/'PlayerTradeGatewayLab';proofs={k:Path(p) for k,p in plan['proofs'].items()}
    assert set(proofs)=={'codec','state','controller','real','native_real','ui','handover','native_build','content'}
    for key,path in proofs.items():
        assert path.resolve().is_relative_to(workspace.resolve()) and path.is_file()
        assert digest(path)==plan['evidence'][str(path)]
    assert set(plan['evidence'])=={str(p) for p in proofs.values()}
    codec=read(proofs['codec']);assert codec['passed'] and codec['checks']>=146 and codec['candidate_dispatch_enabled'] and not codec['candidate_debug_trace']
    assert not codec['ui_installed'] and codec['normal_runtime_unchanged']
    assert digest(Path(codec['candidate_backend']))==codec['candidate_backend_sha256']
    state=read(proofs['state']);assert state['passed'] and state['checks']>=43 and state['exit_code']==0
    controller=read(proofs['controller']);assert controller['passed'] and controller['checks']>=35 and controller['exit_code']==0
    real=read(proofs['real']);assert real['passed'] and len(real['checks'])>=17 and all(real['checks'].values())
    assert real['candidate_gateway_actions_used'] and real['production_gateway_guards_tested'] and not real['direct_transport_probe'] and not real['ui_installed']
    assert all(real[k] for k in ['normal_shutdown','database_restored','private_server_restored','private_navigation_restored','normal_runtime_unchanged'])
    ui=read(proofs['ui']);assert ui['passed'] and ui['checks']>=28 and ui['exchange_regression_checks']>=34 and ui['normal_installation_modified'] is False
    handover=read(proofs['handover']);assert handover['passed'] and handover['checks']>=27 and handover['actual_viewport_picking'] and handover['normal_installation_modified'] is False
    build=read(proofs['native_build']);assert build['passed'] and build['normal_binary_modified'] is False
    native_real=read(proofs['native_real'])
    assert native_real['passed'] and all(native_real['checks'].values())
    assert {'actual_native_body_drop','actual_native_cancel_preserves_goods','actual_native_partner_item_label','actual_native_accept_button','native_accept_does_not_predict_ownership','actual_native_trade_transfers_goods_and_money','native_commands_forwarded_without_rewrite','native_client_normal_shutdown','native_trade_saved_item_ownership','native_trade_saved_account_realm_balances'} <= native_real['checks'].keys()
    assert all(native_real[k] for k in ['normal_shutdown','database_restored','private_server_restored','private_navigation_restored','normal_runtime_unchanged'])
    assert native_real['production_gateway_guards_tested'] and not native_real['direct_transport_probe'] and not native_real['ui_installed']
    assert native_real['source_inputs'][str(proofs['native_build'])]==digest(proofs['native_build'])
    assert ui['build_receipt_sha256']==handover['build_receipt_sha256']==digest(proofs['native_build'])
    old=read(workspace/'RemoteModelEquipmentLab/native_build.json');before={Path(k).as_posix():v for k,v in old['source_sha256'].items()};current={Path(k).as_posix():v for k,v in build['source_sha256'].items()}
    assert {k for k in current if current[k]!=before.get(k)}=={'DAoCVisualBridge/'+n for n in NATIVE}
    predecessor=workspace/'RemoteModelEquipmentLab/installed.json';assert digest(predecessor)==plan['predecessor_sha256'] and read(predecessor)['installed']
    assert plan['native_before_sha256']==build['normal_binary_sha256']==read(predecessor)['native_after_sha256']
    assert plan['native_after_sha256']==build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll']
    expected=inventory(workspace,install,proofs['codec']);rows={r['target']:r for r in plan['files']}
    assert len(rows)==len(plan['files'])==len(expected)==22 and set(rows)=={str(t) for _,t in expected}
    for source,target in expected:
        row=rows[str(target)];assert row['source']==str(source) and digest(source)==row['after_sha256']
        if after:assert target.is_file() and digest(target)==row['after_sha256']
        else:assert (digest(target) if target.exists() else None)==row['before_sha256']
    # The only core decoder difference is the original 0xEA dispatch. Debug sends
    # and unrelated network edits are not deployable through this manifest.
    repo=Path(__file__).resolve().parents[3];core=repo/'source/new-client/godot/game/net/DaocClient.cs';candidate=next(s for s,t in expected if t==core)
    old_core=workspace/'RemotePlayerLab/BackendSource/game/net/DaocClient.cs'
    text=old_core.read_text(encoding='utf-8-sig');needle='\t\t\tcase 0x21:';assert text.count(needle)==1
    assert candidate.read_text(encoding='utf-8-sig')==text.replace(needle,'\t\t\tcase 0xEA: return ReadTradeWindow1127(r);\n'+needle,1)
    assert 'QA_TRADE_SEND' not in candidate.read_text(encoding='utf-8-sig')
    # A proof's pre-install source may only change through an explicitly listed
    # before->after row; no broad bypass for historical evidence.
    for proof in [codec,state,controller,real,native_real]:
        for name,sha in proof.get('source_inputs',{}).items():
            path=Path(name);actual=digest(path)
            if actual==sha:continue
            row=rows.get(str(path));assert after and row and row['before_sha256']==sha and row['after_sha256']==actual
    content=read(proofs['content']);assert content['passed'] and digest(Path(content['source_art']))==digest(Path(content['candidate_art']))==content['sha256']
    return plan

def prepare(workspace,install,proofs):
    from central_activation_receipts import verify_files
    assert verify_files(workspace)['remote_model_equipment_installed']
    build=read(proofs['native_build']);pairs=inventory(workspace,install,proofs['codec'])
    plan=dict(phase='prepared',database_modified=False,server_rules_modified=False,map_modified=False,normal_installation_modified=False,
        predecessor_sha256=digest(workspace/'RemoteModelEquipmentLab/installed.json'),native_before_sha256=build['normal_binary_sha256'],native_after_sha256=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'],
        proofs={k:str(p) for k,p in proofs.items()},evidence={str(p):digest(p) for p in proofs.values()},files=[dict(source=str(s),target=str(t),before_sha256=digest(t) if t.exists() else None,after_sha256=digest(s)) for s,t in pairs])
    validate(workspace,install,plan)
    out=workspace/'PlayerTradeGatewayLab/delivery-plan.json';out.write_text(json.dumps(plan,indent=2));return dict(passed=True,files=len(plan['files']),plan=str(out),installed=False)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install','codec','state','controller','real','native_real','ui','handover']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();workspace=a.workspace.resolve();proofs={k:getattr(a,k).resolve() for k in ['codec','state','controller','real','native_real','ui','handover']};proofs.update(native_build=workspace/'PlayerTradeGatewayLab/native_build.json',content=workspace/'PlayerTradeUILab/content_verified.json');print(json.dumps(prepare(workspace,a.install.resolve(),proofs)))
