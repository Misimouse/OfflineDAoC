"""Reuse the private two-player harness against installed files, never a played DB."""
import argparse,json,os,runpy,sys
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install):
    from player_trade_receipts import verify as verify_installed
    installed,_=verify_installed(workspace);assert installed
    qa=Path(__file__).resolve().parent
    original=qa/'verify_remote_player_real.py'
    text=original.read_text()
    def replace(old,new):
        nonlocal text
        assert text.count(old)==1,old
        text=text.replace(old,new,1)
    replace("SOURCE=source_qa.parent/'Godot' if trade_gateway_probe else ROOT/'Godot' if model_roundtrip or trade_probe else source_qa.parent/'Godot'","SOURCE=ROOT/'Godot'")
    line=next(l for l in text.splitlines() if l.startswith('D=ROOT/'))
    replace(line,"D=ROOT/'PlayerTradeLifecycleLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)")
    replace("assert all(digest(Path(p))==sha for p,sha in backend['source_inputs'].items())","from player_trade_receipts import verify as verify_trade, predecessor_hash\n  _,trade_rows=verify_trade(ROOT)\n  assert all(predecessor_hash(Path(p),trade_rows)==sha for p,sha in backend['source_inputs'].items())")
    replace("if trade_probe:origin=Path(backend['candidate_backend']).parent/name","if trade_probe:origin=INSTALL/'new-client/godot/.godot/mono/temp/bin/Debug'/name")
    replace('from player_trade_wire_case import run','from player_trade_lifecycle_case import run')
    out=workspace/'PlayerTradeLifecycleLab/Runners'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    runner=out/'verify_installed.py';runner.write_text(text)
    os.environ.update(DAOC_INSTALL=str(install),DAOC_BRIDGE_SOURCE_QA=str(qa),DAOC_PLAYER_TRADE_PROBE='1',DAOC_PLAYER_TRADE_STATE_PROBE='1',DAOC_PLAYER_TRADE_CONTROLLER_PROBE='1',DAOC_PLAYER_TRADE_GATEWAY_PROBE='1',DAOC_PLAYER_TRADE_NATIVE_UI_PROBE='0',DAOC_REMOTE_MODEL_ROUNDTRIP='0')
    plan=json.loads((workspace/'PlayerTradeGatewayLab/delivery-plan.json').read_text())
    os.environ['DAOC_PLAYER_TRADE_BACKEND_PROOF']=plan['proofs']['codec']
    sys.path.insert(0,str(workspace/'ProtocolQA'))
    namespace=runpy.run_path(str(runner),run_name='__main__')
    proof=namespace['D']/'verified.json';report=json.loads(proof.read_text());assert report['passed']
    assert report['source_inputs'][str(install/'new-client/godot/.godot/mono/temp/bin/Debug/MMOEngine.dll')]==digest(install/'new-client/godot/.godot/mono/temp/bin/Debug/MMOEngine.dll')
    assert verify_installed(workspace)[0]['installed']
    data=dict(passed=True,installed_files=True,checks=len(report['checks']),proof=str(proof),proof_sha256=digest(proof),harness_source_sha256=digest(original),normal_runtime_modified=False)
    (workspace/'PlayerTradeLifecycleLab/verified.json').write_text(json.dumps(data,indent=2));return data

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve())))
