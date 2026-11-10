"""Explicit, hash-pinned player-trade successor; never infer server outcomes."""
from pathlib import Path
from player_trade_delivery_plan import read, validate as validate_plan
from prepare_combined_expansion_data import digest

def verify(workspace):
    receipt=workspace/'PlayerTradeGatewayLab/installed.json'
    if not receipt.exists():return None,{}
    data=read(receipt)
    if not data.get('installed'):return None,{}
    assert data['phase']=='complete'
    assert not any(data[k] for k in ['database_modified','server_rules_modified','map_modified'])
    path=workspace/'PlayerTradeGatewayLab/delivery-plan.json'
    assert digest(path)==data['plan_sha256']
    plan=read(path)
    assert data['files']==plan['files']
    assert data['native_before_sha256']==plan['native_before_sha256']
    assert data['native_after_sha256']==plan['native_after_sha256']
    from quest_reward_delivery import verify_installed as verify_quest_rewards
    from inventory_quantity_receipts import compose
    _, successor_rows=verify_quest_rewards(workspace)
    validate_plan(workspace,Path(data['install_root']),plan,after=True,successor_rows=successor_rows)
    guards=workspace/'PlayerTradeGatewayLab/delivery_guards_verified.json'
    assert digest(guards)==data['guards_sha256']
    assert read(guards)['passed'] and read(guards)['checks']>=17
    assert read(guards)['plan_sha256']==digest(path)
    return data,compose({r['target']:r for r in data['files']},successor_rows)

def predecessor_hash(path,replacements):
    row=replacements.get(str(path))
    actual=digest(path)
    if not row:return actual
    assert actual==row['after_sha256']
    return row['before_sha256']
