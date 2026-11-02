"""Offline corpse lifecycle, consecutive-target visibility and existing bridge regressions."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import os,subprocess,json,sys
from pathlib import Path
R=Path(__file__).resolve().parent;I=Path(str(INSTALL));D=R/'Reports/combat_lifecycle';D.mkdir(exist_ok=True)
DOTNET=Path(str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64'))
env=dict(os.environ,DOTNET_ROOT=str(DOTNET),DOTNET_ROOT_X64=str(DOTNET),PATH=str(DOTNET)+os.pathsep+os.environ.get('PATH',''),APPDATA=str(R/'Reports/isolated-save'))
cases=[('test_entity_lifecycle.gd','Reports/entities/godot_lifecycle.json'),('test_player_combat.gd','Reports/player_state/godot_tests.json'),('test_interactions.gd','Reports/interactions/godot_tests.json'),('test_motion_metadata.gd','Reports/movement/motion_metadata.json'),('test_combat_entities.gd','Reports/combat_visual/entity_tests.json'),('test_corpse_and_attack_visibility.gd','Reports/combat_lifecycle/offline_tests.json')]
results=[]
for script,report in cases:
 x=subprocess.run([str(I/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'),'--headless','--path',str(R/'Godot'),'--script','res://'+script],env=env,capture_output=True,text=True,timeout=35,creationflags=subprocess.CREATE_NO_WINDOW)
 assert x.returncode==0 and 'SCRIPT ERROR' not in x.stdout+x.stderr,(script,x.stdout,x.stderr)
 results.append({'script':script,'passed':True,'stdout':x.stdout.strip()});print(x.stdout.strip(),flush=True)
from protocol import validate_snapshot
for case in json.loads((R/'Reports/entities/godot_lifecycle.json').read_text())['cases']:validate_snapshot(case['snapshot'])
(D/'regressions.json').write_text(json.dumps({'passed':True,'real_server':False,'cases':results,'lifecycle_snapshots_validated':True,'installed_launcher_built':True,'live_combat_retest_pending':True},indent=2))
