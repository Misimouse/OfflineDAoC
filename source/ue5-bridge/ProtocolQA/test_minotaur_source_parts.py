import unittest
from minotaur_source_parts import resolve_parts


class PartsTests(unittest.TestCase):
    def block(self):
        return [[str(i)+'.499289', 'Original', 'mesh'+str(i), '4', '1', '20', ''] for i in range(1400,1469)]

    def test_original_block_retains_rows_and_all_integer_parts(self):
        rows=[['1','Original','head','4','1','7','']]+self.block()
        parts, aliases=resolve_parts(rows)
        self.assertEqual(len(parts),70)
        self.assertEqual(len(aliases),69)
        self.assertIs(parts['1434'], rows[35])
        self.assertEqual(parts['1434'][0],'1434.499289')

    def test_collision_rejected(self):
        with self.assertRaisesRegex(ValueError,'Ambiguous'):
            resolve_parts(self.block()+[['1434','Collision','other','4','1','20']])

    def test_partial_block_rejected(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            resolve_parts(self.block()[:-1])

    def test_unknown_decimal_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unreviewed'):
            resolve_parts([['1500.1','Other','mesh','4','1','20']])

    def test_unexpected_rounding_rejected(self):
        rows=self.block();rows[0][0]='1400.9'
        with self.assertRaisesRegex(ValueError,'Unexpected'):
            resolve_parts(rows)

    def test_existing_integer_tables_unchanged(self):
        row=['1','Original','head','4','1','7','']
        self.assertEqual(resolve_parts([row]),({'1':row},{}))


if __name__=='__main__':
    unittest.main()
