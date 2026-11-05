using System.Linq;
using DOL.GS.PlayerClass;
using NUnit.Framework;

namespace DOL.GS.Tests
{
    [TestFixture]
    public class UT_SharEligibility
    {
        [Test]
        public void AdvancedChoices_MatchPinnedOriginalSharDefaults()
        {
            var classes = new ICharacterClass[]
            {
                new ClassBainshee(), new ClassEldritch(), new ClassEnchanter(),
                new ClassMentalist(), new ClassBlademaster(), new ClassHero(),
                new ClassChampion(), new ClassWarden(), new ClassDruid(), new ClassBard(),
                new ClassNightshade(), new ClassRanger(), new ClassAnimist(),
                new ClassValewalker(), new ClassVampiir(), new ClassMaulerHib()
            };

            Assert.That(classes.Where(characterClass => characterClass.EligibleRaces.Any(race => race.ID == eRace.Shar))
                .Select(characterClass => characterClass.GetType().Name), Is.EquivalentTo(new[]
                {
                    nameof(ClassMentalist), nameof(ClassBlademaster), nameof(ClassHero),
                    nameof(ClassChampion), nameof(ClassRanger), nameof(ClassVampiir)
                }));
        }

        [Test]
        public void BaseClasses_AcceptOriginalSharProgression()
        {
            foreach (var characterClass in new ICharacterClass[] { new ClassMagician(), new ClassGuardian(), new ClassStalker() })
            {
                Assert.That(characterClass.EligibleRaces.Any(race => race.ID == eRace.Shar), Is.True);
            }

            Assert.That(new ClassNaturalist().EligibleRaces.Any(race => race.ID == eRace.Shar), Is.False);
            Assert.That(new ClassForester().EligibleRaces.Any(race => race.ID == eRace.Shar), Is.False);
        }

        [Test]
        public void StartingStats_KeepOriginalValuesAndLeaveMinotaurPending()
        {
            var stats = GlobalConstants.STARTING_STATS_DICT[eRace.Shar];
            Assert.That(new[] { stats[eStat.STR], stats[eStat.CON], stats[eStat.DEX], stats[eStat.QUI],
                stats[eStat.INT], stats[eStat.PIE], stats[eStat.EMP], stats[eStat.CHR] },
                Is.EqualTo(new[] { 60, 80, 50, 50, 60, 60, 60, 60 }));
            Assert.That(GlobalConstants.STARTING_STATS_DICT.ContainsKey(eRace.HiberniaMinotaur), Is.False);
        }

        [Test]
        public void Vampiir_KeepsAllThreeOriginalRaceChoices()
        {
            Assert.That(new ClassVampiir().EligibleRaces.Select(race => race.ID),
                Is.EquivalentTo(new[] { eRace.Celt, eRace.Lurikeen, eRace.Shar }));
        }

        [TestCase(9, false, 29)]
        [TestCase(10, true, 30)]
        [TestCase(11, false, 32)]
        public void CreationPoints_UseSharBaseAndRequireExactlyThirty(int dexterityBonus, bool expected, int expectedCost)
        {
            var baseStats = GlobalConstants.STARTING_STATS_DICT[eRace.Shar];
            var allocated = baseStats.ToDictionary(pair => pair.Key, pair => pair.Value);
            allocated[eStat.STR] += 10;
            allocated[eStat.CON] += 10;
            allocated[eStat.DEX] += dexterityBonus;

            Assert.That(CharacterStatValidator.Validate(allocated, baseStats,
                eStat.STR, eStat.CON, eStat.DEX, 1, out int points), Is.EqualTo(expected));
            Assert.That(points, Is.EqualTo(expectedCost));
        }
    }
}
