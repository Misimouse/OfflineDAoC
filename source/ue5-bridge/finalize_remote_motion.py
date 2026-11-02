import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/movement'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
assert 'BUILD SUCCESSFUL'in(D/'native_build.log').read_text(errors='replace')
test=read(D/'server_trace.json.motion-results.json');live=read(D/'live_verification.json');metadata=read(D/'godot_tests.json');entities=read(R/'Reports/entities/godot_lifecycle.json.native.json');glyphs=read(R/'Reports/nameplates/render_pixels.json')
assert all(x['passed']for x in [test,live,metadata,entities,glyphs])
files=[];s=R/'Build/DAoCVisualBridge/Binaries'
for p in s.rglob('*'):
 if not p.is_file():continue
 q=R/'Client/Plugins/DAoCVisualBridge/Binaries'/p.relative_to(s);h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==hashlib.sha256(q.read_bytes()).hexdigest();files.append({'path':str(p.relative_to(s)),'sha256':h})
(D/'installed_build.json').write_text(json.dumps({'complete':True,'targets':['UnrealEditor Development','UnrealGame Development','UnrealGame Shipping'],'files':files},indent=2))
x={'passed':True,'installed':True,'recorded_events':test['trace_events'],'raw_max_packet_step_m':test['raw_max_jump_m'],'replay_regular_step_60hz_m':test['smooth_max_regular_step_m'],'recorded_authoritative_corrections_retained':test['authoritative_corrections'],'native_assertions':test['checks'],'native_entity_regression_checks':entities['checks'],'live_sample_pairs_without_new_packet':live['same_packet_active_pairs'],'live_pairs_showing_movement':live['moving_without_new_packet_pairs'],'live_max_regular_observed_step_m':live['max_regular_observed_step_m'],'normal_logout':live['normal_logout'],'movement_cpu_median_ms':live.get('movement_cpu_median_ms'),'movement_cpu_p95_ms':live.get('movement_cpu_p95_ms'),'full_client_feature_parity':False,'map_or_server_ai_changed':False}
(D/'final_summary.json').write_text(json.dumps(x,indent=2));print(json.dumps(x))
