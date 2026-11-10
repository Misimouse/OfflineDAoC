# Quest delivery and reward-window boundary

The installed client passes10 ordinary-server checks for the original Evan's
Notes quest: acceptance grants one letter, delivery consumes it and advances the
journal, the return delivery finishes the quest, stale item requests cannot
repeat the rewards, and completion/experience/inventory save correctly. The
original reward is800 copper and1440 experience in this test. No client grant,
runtime patch or played-data change was needed.

The disposable test stages the original Meara NPC near Evan to isolate delivery
from world travel. It does not prove the route to Mag Mell or expanded world
population. The original target row is read from the normal database using a
read-only connection. NPC staging, database and private server libraries are
restored. The first run exposed a missing laboratory dependency:
classic-quests.json supplies delivery objects through DOL's original helper.
Staging that original configuration temporarily allowed the full test to pass.

Reward quests are a separate remaining gap. The1.127 server inherits the
PacketLib194 quest dialog and modern PacketLib1124 item records. The current
client reads only the title/summary/story, discarding goals, money, experience
percentage, fixed items, choice count and optional items. Its ordinary dialog
response cannot replace QuestRewardChosen0xE8, whose original body has20 bytes
including eight choice-index bytes and quest/giver identities.

Next bounded implementation: strict inactive packet codec/request builder;
then identity-bound state and original dialog art/icons; then real ordinary
server choice/refusal/save tests before guarded installation. Reuse the
original assets. The owner's requested future quest-interface modernization
remains deferred, and this audit does not claim complete mission coverage.
