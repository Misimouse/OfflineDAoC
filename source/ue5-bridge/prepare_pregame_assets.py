"""Stage the installed original pregame artwork without modifying source assets."""
import argparse,hashlib,json,shutil
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--install',required=True,type=Path);parser.add_argument('--bridge-root',required=True,type=Path);args=parser.parse_args()
source=args.install/'new-client/godot/content/pregame';target=args.bridge_root/'Client/Plugins/DAoCVisualBridge/Content/ClassicUI/Pregame';target.mkdir(parents=True,exist_ok=True)
(args.bridge_root/'SourcePregame_v01').mkdir(exist_ok=True)
manifest={}
for folder,names in [('full',['character_selection','character_creation','realm_selection_wide']),('small',['albion_button','hibernia_button','midgard_button','breadcrumbs','misc_pieces_new'])]:
 for name in names:
  src=source/'ui'/folder/(name+'.png');dest=target/(name+'.png');shutil.copy2(src,dest);manifest[name]=hashlib.sha256(dest.read_bytes()).hexdigest()
metadata=json.loads((source/'pregame.json').read_text());(target/'lore.json').write_text(json.dumps({k:metadata[k] for k in ['realm_descriptions','classes','class_lore']},indent=2),encoding='utf-8')
(target/'original_assets.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print('Original pregame artwork staged:',len(manifest))
