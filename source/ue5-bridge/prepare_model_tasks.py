from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
GAME=Path(str(INSTALL / 'new-client/godot'))
seen=json.loads((ROOT/'Reports/live/godot_session.json').read_text())['model_ids']
models=json.loads((GAME/'content/monsters/monsters.json').read_text())
npcs=json.loads((GAME/'content/zones/zone207/npcs.json').read_text())
tasks=[];aliases={};seen_races={}
for ident in seen:
    info=models.get(ident,{})
    if not info.get('race') and not info.get('gltf'):continue
    if str(info.get('figure','')).lower()=='invisible':continue
    race=info.get('race')
    if race and race in seen_races:
        aliases[ident]=seen_races[race];continue
    if race:seen_races[race]=ident
    sample=next((s for s in npcs['spawns'] if str(s.get('model'))==ident),{})
    gear=npcs.get('equipment',{}).get(str(sample.get('equipment','')),[])
    tasks.append(dict(id=ident,info=info,equipment=gear))
(ROOT/'SourceModels').mkdir(exist_ok=True)
(ROOT/'SourceModels/tasks.json').write_text(json.dumps(tasks,indent=2))
(ROOT/'SourceModels/aliases.json').write_text(json.dumps(aliases,indent=2))
print('Model export tasks',len(tasks))
