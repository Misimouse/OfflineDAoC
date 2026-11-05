"""Prevent cross-namespace equipment matches and loss of original mask skins."""
import unittest
from prepare_minotaur_helmet_sources import mask_references


class MaskReferenceTests(unittest.TestCase):
    def rows(self, flag='1', item='2537', skin='5738'):
        header = ['']*98
        header[97] = 'NoArmor Helm'
        row = ['']*98
        row[0], row[2], row[12], row[97] = '4656', item, skin, flag
        return [[], header, row]

    def test_explicit_special_mask_uses_object_id_not_item_id(self):
        result = mask_references(self.rows(), {'2537': ['2537', '', 'mask_eye01_min_m']})
        self.assertEqual(set(result), {4656})
        self.assertEqual(result[4656]['item_id'], 2537)

    def test_numeric_collision_without_special_flag_is_not_a_mask(self):
        self.assertEqual(mask_references(self.rows(flag=''),
                         {'2537': ['2537', '', 'mask_eye01_min_m']}), {})

    def test_other_race_and_effect_items_are_not_relabelled(self):
        for name in ['mask_eye01_sha_m', 'VFX_helmet_NULL-pumpkin']:
            self.assertEqual(mask_references(self.rows(), {'2537': ['2537', '', name]}), {})

    def test_variant_keeps_helm_skin_instead_of_generic_applied_texture(self):
        rows = self.rows(skin='5755')
        rows[-1][22] = '5731'
        result = mask_references(rows, {'2537': ['2537', '', 'mask_plague01_min_m']})
        self.assertEqual(result[4656]['skin_id'], 5755)


if __name__ == '__main__':
    unittest.main()
