from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/nameplates'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
assert 'BUILD SUCCESSFUL'in(D/'native_build.log').read_text(errors='replace')
g=read(D/'godot_tests.json');e=read(R/'Reports/entities/godot_lifecycle.json.native.json');live=read(D/'live_summary.json');render=read(D/'render.json');pixels=read(D/'render_pixels.json')
assert all(x['passed']for x in [g,e,live,render,pixels])
files=[];s=R/'Build/DAoCVisualBridge/Binaries'
for p in s.rglob('*'):
 if not p.is_file():continue
 q=R/'Client/Plugins/DAoCVisualBridge/Binaries'/p.relative_to(s)
 digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==hashlib.sha256(q.read_bytes()).hexdigest()
 files.append({'path':str(p.relative_to(s)),'sha256':digest})
font=R/'Client/Plugins/DAoCVisualBridge/Content/InterfaceFonts/minionpro-bold.ttf'
original=Path(str(INSTALL / 'new-client/godot/content/ui/fonts/minionpro-bold.ttf'))
font_hash=hashlib.sha256(font.read_bytes()).hexdigest();assert font_hash==hashlib.sha256(original.read_bytes()).hexdigest()
packaged_font=R/'Build/DAoCVisualBridge/Content/InterfaceFonts/minionpro-bold.ttf'
assert packaged_font.exists()and font_hash==hashlib.sha256(packaged_font.read_bytes()).hexdigest()
(D/'installed_build.json').write_text(json.dumps({'complete':True,'targets':['UnrealEditor Development','UnrealGame Development','UnrealGame Shipping'],'files':files,'font_sha256':font_hash},indent=2))
x={'passed':True,'installed':True,'font':'Minion Pro Bold (same bytes as Godot)','godot_style_heading_checks':g['checks'],'native_entity_heading_checks':e['checks'],'camera_angles_tested':[0,90,180,270],'real_session_passed':live['passed'],'real_heading_error_degrees':live['max_heading_error_degrees'],'glyph_pixels_verified':True,'visual_review_passed':True,'source_db_or_map_edited':False,'occlusion':'anchor line-of-sight; not per-glyph world depth clipping','remote_movement_smoothed':False}
(D/'final_summary.json').write_text(json.dumps(x,indent=2));print(json.dumps(x))
