"""A declared empty race list must not inherit its parent's allowed races."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

pipeline=Path(__file__).resolve().parents[2]/'new-client/pipeline/build_server_classes.py'
spec=importlib.util.spec_from_file_location('class_catalogue',pipeline)
rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)


class ClassCatalogueParser(unittest.TestCase):
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
