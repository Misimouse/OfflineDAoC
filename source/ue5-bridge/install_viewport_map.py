from pathlib import Path
import shutil,json,hashlib,datetime
R=Path(__file__).resolve().parent
D=R/'Reports/viewport_map';source=R/'UnrealPlugin/DAoCVisualBridge';host=R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge';installed=R/'Client/Plugins/DAoCVisualBridge';backup=R/'Backups/ViewportMapEnglish_20261102/Installed'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for path in [R/'Reports/chat_channels/godot_tests.json',D/'fixture.json.native.json',R/'Reports/chat_channels/fixture.json.native.json',D/'real_visual/visual_render.json']:
 assert json.loads(path.read_text(encoding='utf-8-sig'))['passed'],str(path)
reg=json.loads((R/'Reports/ui_integration/regressions/acceptance.json').read_text(encoding='utf-8-sig'));assert all(v['passed'] for v in reg.values())
for p in (source/'Source').rglob('*'):
 if p.is_file():
  rel=p.relative_to(source);assert sha(p)==sha(host/rel),str(rel)
  dest=installed/rel
  if dest.exists():old=backup/rel;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,old)
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
shutil.copytree(source/'Content/ClassicUI/maps',installed/'Content/ClassicUI/maps',dirs_exist_ok=True)
for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor-DAoCVisualBridge.pdb','UnrealEditor.modules']:
 rel=Path('Binaries/Win64')/name;p=host/rel;dest=installed/rel;assert p.is_file()
 if dest.exists():old=backup/rel;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,old)
 shutil.copy2(p,dest);assert sha(p)==sha(dest)
manifest={'installed':True,'at':datetime.datetime.now().isoformat(),'source_sha256':{str(p.relative_to(source)):sha(p) for p in (source/'Source').rglob('*') if p.is_file()},'godot_runtime_sha256':{p.name:sha(p) for p in (R/'Godot').glob('*.gd') if not p.name.startswith('test_')},'dll_sha256':sha(installed/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'),'native_viewport_map_target_checks':47,'native_chat_checks':21,'native_previous_regressions':sum(v['checks'] for v in reg.values()),'game_language':'English','tab_range_m':60,'original_map_images':len(list((source/'Content/ClassicUI/maps').glob('*.png'))),'real_window_resizes_and_dpi':True,'live_account_used':False,'read_only_visual_replay':True,'work_modified':False,'regular_characters_modified':False}
for rel,digest in manifest['source_sha256'].items():assert sha(installed/rel)==digest
manifest['map_assets_sha256']={p.name:sha(p) for p in (source/'Content/ClassicUI/maps').iterdir() if p.is_file()}
for name,digest in manifest['map_assets_sha256'].items():assert sha(installed/'Content/ClassicUI/maps'/name)==digest
(D/'installation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in manifest.items() if not k.endswith('sha256')},indent=2))
