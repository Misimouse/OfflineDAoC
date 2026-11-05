"""Stage only canonical Shar race tables in an older private protocol fixture."""
import ast
import re


def apply(text, canonical):
    for table, addition in [('RACES',18),('RACE_BY_NAME','Shar'),('RACE_STATS',18)]:
        pattern=r'(const '+table+r'\s*:=\s*)(\{.*?\})'
        old=re.search(pattern,text,re.S);new=re.search(pattern,canonical,re.S)
        assert old and new, ('Missing original transport table',table)
        original,expected=ast.literal_eval(old[2]),ast.literal_eval(new[2])
        assert addition in expected
        assert addition not in original or original[addition]==expected[addition], ('Conflicting existing Shar metadata',table)
        assert set(expected)-set(original) <= {addition}, ('Unexpected transport additions',table)
        assert all(key==addition or expected.get(key)==value for key,value in original.items()), ('Unrelated original race metadata differs',table)
        text=text[:old.start(2)]+new[2]+text[old.end(2):]
    return text
