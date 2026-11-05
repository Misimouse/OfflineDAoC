"""A declared empty race list must not inherit its parent's allowed races."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

pipeline=Path(__file__).resolve().parents[2]/'new-client/pipeline/build_server_classes.py'
spec=importlib.util.spec_from_file_location('class_catalogue',pipeline)
rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)


class ClassCatalogueParser(unittest.TestCase):
    def test_minotaur_gender_aliases_come_from_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'GlobalConstants.cs').write_text('''
RACE_GENDER_CONSTRAINTS_DICT = new Dictionary<eRace, eGender>() {
 // {eRace.Celt, eGender.Female},
 {eRace.AlbionMinotaur, eGender.Male},
 {eRace.MidgardMinotaur, eGender.Male},
 {eRace.HiberniaMinotaur, eGender.Male},
};
''')
            previous=rules.GS
            try:
                rules.GS=root
                self.assertEqual(rules.race_gender_constraints(),{'19':'male','20':'male','21':'male'})
            finally:rules.GS=previous

    def test_missing_race_constraints_preserve_legacy_catalogue(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'GlobalConstants.cs').write_text('class Legacy {}')
            previous=rules.GS
            try:
                rules.GS=root
                self.assertEqual(rules.race_gender_constraints(),{})
            finally:rules.GS=previous

    def test_gender_constraints_come_from_server_and_ignore_comments(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'GlobalConstants.cs').write_text('''
public static readonly Dictionary<eCharacterClass, eGender> CLASS_GENDER_CONSTRAINTS_DICT = new()
{
 // {eCharacterClass.Magician, eGender.Male},
 {eCharacterClass.Bainshee, eGender.Female},
 {eCharacterClass.Valkyrie, eGender.Female},
};
''')
            previous=rules.GS
            try:
                rules.GS=root
                self.assertEqual(rules.class_gender_constraints(),{'Bainshee':'female','Valkyrie':'female'})
            finally:rules.GS=previous

    def test_target_typed_empty_list_overrides_inheritance(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);classes=root/'playerclasses';classes.mkdir()
            (classes/'ClassMagician.cs').write_text('''
[CharacterClass((int)eCharacterClass.Magician, "Magician", "Magician")]
class ClassMagician : CharacterClass {
 public override List<PlayerRace> EligibleRaces => new List<PlayerRace>() { PlayerRace.Celt, PlayerRace.Elf };
}
''')
            (classes/'ClassBainshee.cs').write_text('''
[CharacterClass((int)eCharacterClass.Bainshee, "Bainshee", "Magician")]
class ClassBainshee : ClassMagician {
 public override List<PlayerRace> EligibleRaces => new() { /* currently disabled */ };
}
''')
            previous=rules.GS
            try:
                rules.GS=root;parsed=rules.parse_classes()
            finally:rules.GS=previous
            self.assertEqual(parsed['ClassMagician']['races'],[9,11])
            self.assertEqual(parsed['ClassBainshee']['races'],[])


if __name__=='__main__':unittest.main()
