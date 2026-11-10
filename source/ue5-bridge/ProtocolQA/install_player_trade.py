"""Back up and atomically account for the exact tested client trade delivery."""
import argparse,json,shutil,socket
from datetime import datetime
from pathlib import Path
from player_trade_delivery_plan import read,validate
from prepare_combined_expansion_data import digest

def install(workspace,game):
    from central_activation_receipts import verify_files
    assert verify_files(workspace)['remote_model_equipment_installed']
    root=workspace/'PlayerTradeGatewayLab';path=root/'delivery-plan.json'
    plan=read(path);validate(workspace,game,plan)
    receipt=root/'installed.json'
    assert not receipt.exists() or not read(receipt).get('installed')
    guards=root/'delivery_guards_verified.json'
    assert read(guards)['passed'] and read(guards)['checks']>=17
    assert read(guards)['plan_sha256']==digest(path)
    # The original server and client must be closed; WORK's editor is unrelated.
    for port in [10300,19727]:
        with socket.socket() as probe:
            probe.settimeout(.3)
            assert probe.connect_ex(('127.0.0.1',port))!=0,'Close normal server/client before delivery'
    backup=workspace/'Backups'/('PlayerTrade_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True)
    recovery=dict(phase='backing_up',files=[],database_modified=False)
    recovery_path=backup/'recovery.json'
    def save():recovery_path.write_text(json.dumps(recovery,indent=2))
    for n,row in enumerate(plan['files']):
        target=Path(row['target']).resolve()
        assert any(target.is_relative_to(p.resolve()) for p in [workspace,game/'new-client',Path(__file__).resolve().parents[3]])
        saved=backup/str(n)
        if target.exists():shutil.copy2(target,saved);assert digest(saved)==row['before_sha256']
        recovery['files'].append(dict(target=str(target),backup=str(saved) if target.exists() else None,before_sha256=row['before_sha256']))
        save()
    try:
        recovery['phase']='copying';save()
        for row in plan['files']:
            target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(row['source'],target);assert digest(target)==row['after_sha256']
        data=dict(installed=True,phase='complete',install_root=str(game),backup=str(backup),
            plan_sha256=digest(path),guards_sha256=digest(guards),files=plan['files'],
            native_before_sha256=plan['native_before_sha256'],native_after_sha256=plan['native_after_sha256'],
            database_modified=False,server_rules_modified=False,map_modified=False)
        receipt.write_text(json.dumps(data,indent=2))
        from player_trade_receipts import verify
        verify(workspace)
        central=verify_files(workspace)
        recovery['phase']='complete';save()
        (root/'installed_verification.json').write_text(json.dumps(central,indent=2))
        return dict(passed=True,installed=True,files=len(plan['files']),backup=str(backup))
    except BaseException:
        for row in reversed(recovery['files']):
            target=Path(row['target'])
            if row['backup']:shutil.copy2(row['backup'],target);assert digest(target)==row['before_sha256']
            elif target.exists():target.unlink()
        receipt.write_text(json.dumps(dict(installed=False,phase='rolled_back',backup=str(backup))))
        recovery['phase']='rolled_back';save();verify_files(workspace)
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(install(a.workspace.resolve(),a.install.resolve())))
