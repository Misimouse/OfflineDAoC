"""Reject unrelated or conflicting protocol metadata while preparing a private Shar fixture."""
import unittest
from shar_transport_metadata import apply


ORIGINAL='''const RACES := {9: ["Celt", "cel", 302, 310]}
const RACE_BY_NAME := {"Celt": 9}
const RACE_STATS := {9: [60,60,60,60,60,60,60,60]}
func preserve_original_logic(): pass
'''
CANONICAL=ORIGINAL.replace('302, 310]}','302, 310], 18: ["Shar", "sha", 1075, 1087]}').replace('"Celt": 9}','"Celt": 9, "Shar": 18}').replace('60,60,60,60,60,60,60,60]}','60,60,60,60,60,60,60,60],18:[60,50,80,50,60,60,60,60]}')


class SharTransportGuards(unittest.TestCase):
    def test_scope_and_repeat_are_stable(self):
        updated=apply(ORIGINAL,CANONICAL)
        self.assertEqual(updated,CANONICAL)
        self.assertEqual(apply(updated,CANONICAL),updated)
        self.assertTrue(updated.endswith('func preserve_original_logic(): pass\n'))

    def test_existing_original_race_conflict_is_rejected(self):
        with self.assertRaisesRegex(AssertionError,'Unrelated original race'):
            apply(ORIGINAL.replace('302, 310','999, 310'),CANONICAL)

    def test_existing_shar_conflict_is_rejected(self):
        with self.assertRaisesRegex(AssertionError,'Conflicting existing Shar'):
            apply(CANONICAL.replace('1075, 1087','1419, 1419'),CANONICAL)

    def test_unrelated_new_race_is_rejected(self):
        with self.assertRaisesRegex(AssertionError,'Unexpected transport additions'):
            apply(ORIGINAL,CANONICAL.replace('302, 310],','302, 310],10:["Firbolg","fir",286,294],'))


if __name__=='__main__':unittest.main()
