from pathlib import Path
import json,runpy,hashlib
R=Path(__file__).resolve().parent
# Reuse the established source extractor and texture deduplication, preserving spell IDs.
ctx=runpy.run_path(str(R/'export_spell_visuals.py'))
G,D,extract,texture=ctx['G'],ctx['D'],ctx['extract'],ctx['texture']
files,textures=ctx['files'],ctx['textures']
catalog=json.loads((D/'catalog.json').read_text())
source=json.loads((G/'content/weapons/weapon_effects.json').read_text())
catalog['weapon_effects']={}
for ident,path in source.items():
    p=G/path.removeprefix('res://');assert p.exists(),path
    key=hashlib.sha256(path.encode()).hexdigest()[:16]
    if key not in files:
        data=extract(p);files[key]=data;(D/'Data'/(key+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    catalog['weapon_effects'][ident]={'data':key,'source':path}
catalog['textures']={key:'/DAoCVisualBridge/SpellVisuals_v01/Textures/T_'+key+'.T_'+key for key in textures}
(D/'catalog.json').write_text(json.dumps(catalog,separators=(',',':')),encoding='utf-8')
(R/'SourceSpellVisuals_v01/textures.json').write_text(json.dumps(textures),encoding='utf-8')
report={'passed':True,'weapon_effects':len(source),'total_textures':len(textures),'data_files':len(files),'mesh_parts':sum(len(files[v['data']]['parts']) for v in catalog['weapon_effects'].values()),'emitters':sum(len(files[v['data']]['particles']) for v in catalog['weapon_effects'].values())}
(R/'Reports/training_staff_fx_pets/weapon_fx_export.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(report)
