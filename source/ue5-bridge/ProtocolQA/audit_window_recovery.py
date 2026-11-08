"""Compare original recoverable windows with existing native window implementations."""
import argparse,ast,json,re
from pathlib import Path
from prepare_combined_expansion_data import digest

def audit(workspace,install):
    source=Path(__file__).resolve().parents[1]
    original=install/'new-client/godot/game/ui/game_ui.gd'
    options=install/'new-client/godot/game/ui/options_window.gd'
    native=source/'UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeWindowRecovery.cpp'
    windows=ast.literal_eval(re.search(r'const RESTORABLE := (\[\[.*?\]\])',original.read_text(encoding='utf-8-sig'),re.S).group(1))
    supported={'panel','chat_combat','minigroup','map','journal','guild'}
    assert supported.issubset({row[0] for row in windows})
    native_text=native.read_text(encoding='utf-8-sig')
    assert all('Id==TEXT("'+name+'")' in native_text for name in supported)
    rows=[]
    automatic={'status','chat','quickbar1','quickbar2','quickbar3','minipet','conc','benefits','target'}
    for name,label in windows:
        rows.append(dict(id=name,label=label,status='existing_native_toggle_connected' if name in supported else 'existing_native_always_visible_or_server_driven' if name in automatic else 'separate_surface_not_added_by_this_package'))
    result=dict(passed=True,original_windows=len(windows),connected_windows=len(supported),windows=rows,
        source_inputs={str(p):digest(p) for p in [original,options,native]},
        scope='Original open/close semantics for six existing closable native windows, plus existing layout recovery; not full Options parity',
        preserved=['inventory','quickbar_actions','chat_filters','key_bindings','ui_scale','played_database','server_rules'],
        normal_installation_modified=False,database_modified=False)
    out=workspace/'WindowRecoveryLab/reference_audit.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return dict(passed=True,original_windows=len(windows),connected_windows=len(supported),output=str(out))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.workspace.resolve(),a.install.resolve())))
