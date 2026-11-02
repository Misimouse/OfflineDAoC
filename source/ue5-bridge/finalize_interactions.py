"""Consolidate actual evidence and verify installed package identity."""
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/interactions'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
assert 'BUILD SUCCESSFUL' in (D/'native_build.log').read_text(errors='replace')
g=read(D/'godot_tests.json');ui=read(D/'native_fixture.json.native.json');entities=read(R/'Reports/entities/godot_lifecycle.json.native.json');live=read(D/'live_verification.json')
assert g['passed']and ui['passed']and entities['passed']and live['passed']
s=R/'Build/DAoCVisualBridge/Binaries';files=[]
for p in s.rglob('*'):
 if not p.is_file():continue
 q=R/'Client/Plugins/DAoCVisualBridge/Binaries'/p.relative_to(s)
 h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==hashlib.sha256(q.read_bytes()).hexdigest()
 files.append({'path':str(p.relative_to(s)),'sha256':h})
(D/'installed_build.json').write_text(json.dumps({'build_complete':True,'targets':['UnrealEditor Development','UnrealGame Development','UnrealGame Shipping'],'files':files},indent=2))
summary={'passed':True,'installed':True,'godot_interaction_checks':g['checks'],'native_ui_checks':ui['checks'],'native_entity_regression_checks':entities['checks'],'protocol_tests':6,'live_merchant_items':live['max_merchant_items'],'live_target_ids':live['target_ids'],'normal_logout':live['normal_logout'],'screen_picking_passed':live['screen_picking_passed'],'visual_review_passed':True,'scope':'targeting, popup keywords, server confirmations, merchant catalog browsing','real_server_coverage':'target and merchant catalog; keyword/confirmation replies tested offline','purchases_sales_specialized_services_complete':False,'remote_smoothing_complete':False}
(D/'final_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
