"""Extend the private expansion UI fixture using the joint server's Vampiir rules."""
import argparse
import json
from pathlib import Path


def prepare(source, classes, output):
    fixture=json.loads(source.read_text())
    rules=json.loads(classes.read_text())
    assert rules['classes']['58']['races']==[9,12,18]
    assert rules['race_genders']['21']=='male'
    assert fixture['test_race']=='Minotaur' and not fixture['test_female']
    choices=[c for c in fixture['character_lobby']['choices'] if c['class_id']!=58]
    for race in ['Celt','Lurikeen','Shar']:
        for female in [False,True]:
            choices.append({'id':race+(':'+('f' if female else 'm'))+':58',
                            'race':race,'female':female,'class_id':58,'class_name':'Vampiir'})
    fixture['character_lobby']['choices']=choices
    counts={'bainshee':sum(c['class_id']==39 for c in choices),
            'vampiir':sum(c['class_id']==58 for c in choices),
            'shar':sum(c['race']=='Shar' for c in choices),
            'minotaur':sum(c['race']=='Minotaur' for c in choices)}
    assert counts=={'bainshee':3,'vampiir':6,'shar':12,'minotaur':4},counts
    # The earlier synthetic Minotaur fixture reused a Shar overview. Make its
    # identity consistent instead of relying on the explicit prefix to win.
    character=fixture['character_lobby']['characters'][fixture['test_slot']]
    assert character['prefix']=='mino' and character['race']=='Minotaur'
    overview=character['overview']
    overview.update(name=character['name'],race=21,race_name='Minotaur',model=1419,
                    class_id=52,gender=0,stats=[80,50,70,40,60,60,60,60])
    assert output.resolve().parent.name=='CombinedExpansionLobbyAcceptance'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(fixture,indent=2),encoding='utf-8')
    return {'passed':True,'live_account':False,'choices':counts,'fixture':str(output)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['source','classes','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.source,args.classes,args.output)))
