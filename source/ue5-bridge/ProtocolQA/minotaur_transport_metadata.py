"""Stage exact canonical Minotaur packet metadata only in the disposable fixture."""
import re
from shar_transport_metadata import apply as apply_tables


def apply(text, canonical):
    text=apply_tables(text,canonical)
    old='"prefix": "%s_%s" % [race[1], "f" if female else "m"],'
    new='"prefix": String(race[1]) if race[1]=="mino" else "%s_%s" % [race[1], "f" if female else "m"],'
    assert canonical.count(new)==1
    if new not in text:
        assert text.count(old)==1
        text=text.replace(old,new,1)
    guard='\tif int(RACES[race_id][3 if female else 2])<=0:\n\t\treturn "This race does not support that gender."\n'
    assert guard in canonical
    if guard not in text:
        anchor='\tif race_id == 0:\n\t\treturn "Unknown race."\n'
        assert text.count(anchor)==1
        text=text.replace(anchor,anchor+guard,1)
    return text
