"""Read-only character capability inventory. No account, character or spell grants are changed."""
import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',required=True,type=Path)
    parser.add_argument('--install',required=True,type=Path)
    parser.add_argument('--workspace',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    source=args.repository/'source'
    spec=importlib.util.spec_from_file_location('source_class_rules',source/'new-client/pipeline/build_server_classes.py')
    rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
    rules.GS=source/'server/GameServer'
    ids=rules.enum_values(rules.GS/'Enums/eCharacterClass.cs','eCharacterClass')
    classes={c['enum']:c for c in rules.parse_classes().values()}
    starting=rules.starting_classes().get('Hibernia',[])
    db=args.install/'runtime/data/opendaoc.sqlite3.db'
    with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as conn:
        props=dict(conn.execute("SELECT Key,Value FROM ServerProperty WHERE Key IN ('disabled_classes','disabled_races','start_as_base_class','enable_sluaghbinder')"))
        spell_inventory={str(cid):[{'line':key,'spec':spec_key,'linked_spells':count}
                                 for key,spec_key,count in conn.execute(
            'SELECT l.KeyName,l.Spec,COUNT(x.SpellID) FROM SpellLine l LEFT JOIN LineXSpell x ON x.LineName=l.KeyName '
            'WHERE l.Spec IN (SELECT SpecKeyName FROM ClassXSpecialization WHERE ClassID=?) GROUP BY l.KeyName ORDER BY l.KeyName',(cid,))]
                         for cid in [39,58,62]}
    disabled=rules.id_set(props.get('disabled_classes',''))
    disabled_races=rules.id_set(props.get('disabled_races',''))
    game=args.install/'new-client/godot'
    catalogue=json.loads((game/'content/rules/server_classes.json').read_text())
    appearance=json.loads((args.workspace/'Client/Plugins/DAoCVisualBridge/Content/ClassicUI/Pregame/appearance_catalog.json').read_text())
    figures={v.get('meta',{}).get('prefix') for v in appearance['figures'].values()}
    rows=[]
    for name in starting+['Vampiir','MaulerHib']:
        if any(x['enum']==name for x in rows):continue
        c=classes.get(name)
        rows.append({'enum':name,'id':ids.get(name),'server_source_exists':c is not None,
                     'listed_as_starting':name in starting,'disabled_by_property':ids.get(name) in disabled,
                     'client_creation_catalogue':str(ids.get(name)) in catalogue['classes'],
                     'source_base':c.get('base') if c else None,
                     'source_eligible_races':c.get('races') if c else None})
    races=[]
    for name,prefix,race_id in [('Celt','cel',9),('Firbolg','fir',10),('Elf','elf',11),('Lurikeen','lur',12),('Sylvan','syl',15),('Shar','sha',18),('Hibernia Minotaur',None,21)]:
        races.append({'name':name,'id':race_id,'disabled_by_property':race_id in disabled_races,
                      'godot_figure_metadata':{sex:(game/'content/characters/races'/f'{prefix}_{sex}'/'figure.json').is_file() if prefix else None for sex in ['m','f']},
                      'native_appearance':{sex:f'{prefix}_{sex}' in figures if prefix else None for sex in ['m','f']}})
    result={'read_only':True,'server_properties':props,'classes':rows,'races':races,'expansion_spell_inventory':spell_inventory,
            'limitations':['Source presence does not prove runtime completeness or spell/visual coverage.',
                           'The original look store is local, not cross-client server persistence.',
                           'Minotaur asset mapping is unconfirmed; null means not yet audited.',
                           'Spell-line joins inventory existing data; career implementations may also add shared lines.'],
            'next':['Check source gender restrictions and all creation validators before expansion enablement.',
                    'Inspect the original class/spell database in disposable probes; never grant spells by UI labels.',
                    'Port and verify missing figure metadata, geometry, gear and appearance before exposing a race.']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'read_only':True,'classes':len(rows),'races':len(races),'output':str(args.output)}))


if __name__=='__main__':main()
