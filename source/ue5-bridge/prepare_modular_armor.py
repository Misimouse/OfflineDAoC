"""Resolve original armour textures without changing or copying source game content."""
import json
from bridge_paths import ROOT, INSTALL

base=INSTALL/'new-client/godot/content/characters'
armor=json.loads((base/'armor.json').read_text(encoding='utf-8-sig'))
names={str(a[1]) for model in armor['models'].values() for gender in model.values()
       if isinstance(gender,dict) for a in gender.values() if isinstance(a,list) and len(a)>1}
manifest={};missing=[]
for name in sorted(names):
    path=next((p for folder in ['x4plus','original']
               if (p:=base/'fig3_textures'/folder/(name+'.png')).exists()),None)
    if path:manifest[name]={'file':str(path)}
    else:missing.append(name)
output=ROOT/'SourceArmour';output.mkdir(exist_ok=True)
(output/'textures.json').write_text(json.dumps({'textures':manifest,'models':armor['models'],'missing':missing},indent=2),encoding='utf-8')
print({'armour_models':len(armor['models']),'textures':len(manifest),'missing':len(missing)})
