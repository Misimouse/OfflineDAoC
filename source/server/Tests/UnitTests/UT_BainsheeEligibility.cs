using System.Linq;
using DOL.GS.PlayerClass;
using NUnit.Framework;

namespace DOL.GS.Tests
{
    [TestFixture]
    public class UT_BainsheeEligibility
    {
        [Test]
        public void EligibleRaces_ContainsOnlyTheThreeSupportedOriginalForms()
        {
            var races = new ClassBainshee().EligibleRaces;

            Assert.That(races.Select(race => race.ID),
                Is.EquivalentTo(new[] { eRace.Celt, eRace.Elf, eRace.Lurikeen }));
            Assert.That(races.All(race => race.Realm == eRealm.Hibernia), Is.True);
        }

        [Test]
        public void CreationConstraints_KeepFemaleOnlyAndHibernianStartingClass()
        {
            Assert.That(GlobalConstants.CLASS_GENDER_CONSTRAINTS_DICT[eCharacterClass.Bainshee],
                Is.EqualTo(eGender.Female));
            Assert.That(GlobalConstants.STARTING_CLASSES_DICT[eRealm.Hibernia],
                Does.Contain(eCharacterClass.Bainshee));
            Assert.That(GlobalConstants.STARTING_CLASSES_DICT[eRealm.Albion],
                Does.Not.Contain(eCharacterClass.Bainshee));
            Assert.That(GlobalConstants.STARTING_CLASSES_DICT[eRealm.Midgard],
                Does.Not.Contain(eCharacterClass.Bainshee));
        }

        [TestCase("39", true)]
        [TestCase("38-40", true)]
        [TestCase("Bainshee", true)]
        [TestCase("  bainshee ;58-62", true)]
        [TestCase("20;33;34;58-62", false)]
        [TestCase(null, false)]
        public void TrainerClassSwitch_HandlesNumericRangesAndNames(string disabled, bool expected)
        {
            Assert.That(ClassBainshee.IsDisabledByConfiguration(disabled), Is.EqualTo(expected));
        }
    }
}
