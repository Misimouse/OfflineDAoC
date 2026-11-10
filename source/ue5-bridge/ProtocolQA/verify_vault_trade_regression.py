"""Run original vault persistence against the installed trade client privately."""
import argparse,json,os,runpy,shutil,sqlite3,sys
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install,engine):
    from central_activation_receipts import verify_files
    assert verify_files(workspace)['player_trade_installed']
    os.environ['DAOC_INSTALL']=str(install)
    qa=workspace/'ProtocolQA';sys.path.insert(0,str(qa))
    import qa_runtime as runtime
    assert runtime.ROOT==workspace and runtime.INSTALL==install
    with sqlite3.connect(runtime.DB) as db:
        assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==runtime.RUN.name
    sdk=engine/'Binaries/ThirdParty/DotNet/10.0/win-x64'
    runtime.dotnet=sdk/'dotnet.exe';assert runtime.dotnet.is_file()
    runtime.env.update(DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+runtime.env['PATH'])
    out=workspace/'VaultTradeLifecycleLab'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    source=Path(__file__).with_name('verify_vault_persistence_real.py')
    inputs={str(source):digest(source)}
    normal=install/'new-client/godot/.godot/mono/temp/bin/Debug'
    targets=runtime.RUN/'LobbyProject/.godot/mono/temp/bin/Debug'
    files=[];result=dict(passed=False,installed_client=True,disposable_only=True,normal_runtime_modified=False)
    old_source=os.environ.get('DAOC_BRIDGE_QA_SOURCE')
    recovery=out/'recovery.json'
    try:
        for name in ['MMOEngine.dll','MMOEngine.pdb']:
            origin=normal/name;target=targets/name;saved=out/('before_'+name)
            assert target.resolve().is_relative_to(runtime.RUN.resolve())
            shutil.copy2(target,saved);files.append(dict(target=str(target),backup=str(saved),before_sha256=digest(saved)))
            recovery.write_text(json.dumps(dict(phase='running',files=files),indent=2))
            inputs[str(origin)]=digest(origin);shutil.copy2(origin,target)
        os.environ['DAOC_BRIDGE_QA_SOURCE']=str(workspace/'Godot')
        namespace=runpy.run_path(str(source),run_name='__main__')
        proof=namespace['D']/'real_protocol.json';data=json.loads(proof.read_text())
        assert data['passed'] and data['normal_shutdown'] and data['database_restored'] and data['candidate_server_restored'] and data['normal_runtime_unchanged']
        result.update(passed=True,checks=data['checks'],original_vault_proof=str(proof),original_vault_sha256=digest(proof))
    finally:
        for row in reversed(files):
            target=Path(row['target']);shutil.copy2(row['backup'],target)
            assert digest(target)==row['before_sha256']
        if old_source is None:os.environ.pop('DAOC_BRIDGE_QA_SOURCE',None)
        else:os.environ['DAOC_BRIDGE_QA_SOURCE']=old_source
        result['private_backend_restored']=len(files)==2
        result['source_inputs']=inputs
        assert all(digest(Path(p))==h for p,h in inputs.items())
        assert verify_files(workspace)['player_trade_installed']
        recovery.write_text(json.dumps(dict(phase='restored',files=files),indent=2))
        (out/'verified.json').write_text(json.dumps(result,indent=2))
    return dict(passed=result['passed'],checks=len(result['checks']),proof=str(out/'verified.json'))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install','engine']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve())))
