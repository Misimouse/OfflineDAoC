"""Inventory delivery manifest; explicitly distinguishes untested commerce."""
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/inventory'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
log=(D/'build_full.log').read_text(errors='replace');assert 'BUILD SUCCESSFUL' in log
targets=['UnrealEditor Win64 Development','UnrealGame Win64 Development','UnrealGame Win64 Shipping']
assert all(t in log for t in targets)
files=[]
for folder in ['Binaries','Source']:
 src=R/'Build/DAoCVisualBridge'/folder
 for p in src.rglob('*'):
  if not p.is_file():continue
  q=R/'Client/Plugins/DAoCVisualBridge'/folder/p.relative_to(src);h=hashlib.sha256(p.read_bytes()).hexdigest();assert q.is_file() and h==hashlib.sha256(q.read_bytes()).hexdigest(),str(q)
  files.append({'path':folder+'/'+p.relative_to(src).as_posix(),'sha256':h})
backend={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Godot').glob('*.gd')}
(D/'installed_build.json').write_text(json.dumps({'complete':True,'targets':targets,'files':files,'godot_files':backend},indent=2))
tests=read(D/'godot_tests.json');native=read(D/'fixture.json.native.json');core=read(D/'server_verification.json');visual=read(D/'visual_verification.json');interaction=read(R/'Reports/interactions/godot_tests.json');motion=read(R/'Reports/movement/server_trace.json.motion-results.json');names=read(R/'Reports/nameplates/render_pixels.json')
assert all(x['passed'] for x in [tests,native,core,visual,interaction,motion,names])
assert core['core_inventory_verified'] and core['original_inventory_restored'] and core['normal_logout'] and not core['errors']
result={'installed':True,'passed_core_inventory':True,'godot_checks':tests['checks'],'native_checks':native['checks'],'interaction_regression_checks':interaction['checks'],'motion_regression_checks':motion['checks'],'nameplate_views':len(names['angles']),'real_core_item_requests':core['gateway_inventory']['requests'],'original_inventory_restored':core['original_inventory_restored'],'normal_logout':core['normal_logout'] and visual['normal_logout'],'real_items_displayed':visual['max_items'],'real_commerce_verified':core.get('commerce_live_verified',False),'commerce_test_limit':core.get('commerce_unavailable',''),'full_client_parity':False,'equipment_visual_dressing_complete':False,'original_skin_migrated':False}
(D/'final_summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
