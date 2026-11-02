"""Verify actual rendering and packet-to-actor headings using the normal GM probe."""
import json,shutil,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/nameplates';I=R/'Reports/interactions'
with (D/'live_stdout.log').open('w')as log:p=subprocess.run([sys.executable,str(R/'verify_interactions_live.py')],cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=340)
assert p.returncode==0,'GM probe failed; see nameplates/live_stdout.log'
a=json.loads((I/'live_samples.json').read_text())
rows=[s['unreal']for s in a]
maxnames=max((x.get('nameplates_visible',0)for x in rows),default=0)
error=max((x.get('npc_heading_error_degrees_max',999)for x in rows if x.get('npcs',0)>0),default=999)
font=any(x.get('nameplate_font_exists',False)for x in rows)
levels=sorted(set(s['godot'].get('nameplate_player_level',-1)for s in a))
palettes=[s['godot'].get('nameplate_palette_counts',{})for s in a]
friendly=max((d.get('[175, 223, 208]',0)for d in palettes),default=0)
colors=sorted(set(k for d in palettes for k in d))
for f in ['live_samples.json','live_verification.json','Merchant_GM.png']:shutil.copy2(I/f,D/f)
x={'real_server':True,'passed':maxnames>0 and error<.01 and font and friendly>0,'max_visible_names':maxnames,'max_heading_error_degrees':error,'original_font_exists':font,'player_levels':levels,'friendly_npcs':friendly,'palette_colors':colors,'interaction_probe_passed':True}
(D/'live_summary.json').write_text(json.dumps(x,indent=2));print(json.dumps(x));assert x['passed']
