from pathlib import Path
import shutil,json,hashlib,datetime
R=Path(__file__).resolve().parent
D=R/'Reports/remote_collision';source=R/'UnrealPlugin/DAoCVisualBridge';host=R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge';installed=R/'Client/Plugins/DAoCVisualBridge';backup=R/'Backups/RemoteCollisionNotice_20261102/Installed'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
motion=read(R/'Reports/movement/server_trace.json.motion-results.json');assert motion['passed']
viewport=read(R/'Reports/viewport_map/fixture.json.native.json');assert viewport['passed']
godot=read(R/'Reports/world_messages/godot_tests.json');assert godot['passed']
reg=read(R/'Reports/ui_integration/regressions/acceptance.json');assert all(v['passed'] for v in reg.values())
real=read(D/'real_visual/visual_current.json');nav=real['navigation_probe'];assert nav['passed']
coverage=nav['new_tree_instances_blocked'];assert len(coverage)==12 and all(v>0 for v in coverage.values()),coverage
files=[]
for p in (source/'Source').rglob('*'):
 if p.is_file():
  rel=p.relative_to(source);assert sha(p)==sha(host/rel);files.append((p,rel))
for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor-DAoCVisualBridge.pdb','UnrealEditor.modules']:
 rel=Path('Binaries/Win64')/name;files.append((host/rel,rel))
for p in (source/'Content/NavigationCollision_v02').rglob('*'):
 if p.is_file():
  rel=p.relative_to(source);assert sha(p)==sha(host/rel);files.append((p,rel))
for p,rel in files:
 dest=installed/rel
 if dest.exists():
  old=backup/rel;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,old)
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(dest)==sha(p)
manifest={'installed':True,'at':datetime.datetime.now().isoformat(),'motion_checks':motion['checks'],'native_viewport_checks':viewport['checks'],'godot_message_checks':godot['checks'],'general_regression_checks':sum(v['checks'] for v in reg.values()),'actual_map_navigation':nav,'new_tree_collision_models':12,'collision_catalog_sha256':sha(R/'collision_catalog.json'),'godot_chat_sha256':sha(R/'Godot/chat_state.gd'),'installed_files_sha256':{str(rel):sha(p) for p,rel in files},'work_modified':False,'live_account_used':False,'game_language':'English','region_font_size':24,'region_vertical_viewport_fraction':.4,'region_duration_ms':6500,'original_server_navigation_modified':False,'server_teleports_preserved':True}
(D/'installation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in manifest.items() if k not in ['installed_files_sha256','actual_map_navigation']},indent=2))
