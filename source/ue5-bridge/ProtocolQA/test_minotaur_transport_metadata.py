import unittest
from minotaur_transport_metadata import apply
from test_shar_transport_metadata import ORIGINAL, CANONICAL

LEGACY_PREFIX='"prefix": "%s_%s" % [race[1], "f" if female else "m"],'
PREFIX='"prefix": String(race[1]) if race[1]=="mino" else "%s_%s" % [race[1], "f" if female else "m"],'
ANCHOR='\tif race_id == 0:\n\t\treturn "Unknown race."\n'
GUARD='\tif int(RACES[race_id][3 if female else 2])<=0:\n\t\treturn "This race does not support that gender."\n'
OLD=ORIGINAL+LEGACY_PREFIX+'\n'+ANCHOR
NEW=CANONICAL.replace('1075, 1087]}','1075, 1087],21:["Minotaur","mino",1419,0]}').replace('"Shar": 18}','"Shar": 18,"Minotaur":21}').replace('18:[60,50,80,50,60,60,60,60]}','18:[60,50,80,50,60,60,60,60],21:[80,50,70,40,60,60,60,60]}')+PREFIX+'\n'+ANCHOR+GUARD


class MinotaurTransportGuards(unittest.TestCase):
    def test_exact_metadata_prefix_and_gender_guard(self):
        self.assertEqual(apply(OLD,NEW),NEW)

    def test_repeat_is_identical(self):
        self.assertEqual(apply(NEW,NEW),NEW)

    def test_other_race_conflict_rejected(self):
        with self.assertRaises(AssertionError):
            apply(OLD.replace('302, 310','999, 310'),NEW)

    def test_unknown_prefix_implementation_rejected(self):
        with self.assertRaises(AssertionError):
            apply(OLD.replace(LEGACY_PREFIX,'"prefix":"other",'),NEW)


if __name__=='__main__':
    unittest.main()
