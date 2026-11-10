# Per-character quickbar pages and class switching

A new character inherited the last open character's quickbar page selections.
Entries and macros were already cleared; the page array was not. Resetting the
three pages before loading the new character's saved UI fixes that case while
preserving existing characters' saved pages and same-character working state.

Verification uses a fresh private UI project (56 checks) and an ordinary-player
server scenario (34 checks). The original runtime reproduces the page failure;
the candidate passes it. The real scenario earns level 2, trains Regrowth,
saves a heal on page 4, quits normally, enters a fresh Magician on the same
account, and then returns to the original character. Skills, shortcut identities,
progression and saved pages remain separate. A stale heal command is refused
for the Magician. No spells, items or progression are granted by the bridge.

Delivery replaces only `Godot/classic_ui_state.gd`, with an exact pre-change
baseline, backup, rollback guard, pinned proofs and predecessor receipt. Eighteen
altered-plan checks reject scope or evidence changes. The successor hash is
composed through the existing installation receipt chain. Native binaries, map
assets, server rules and the played database are not replaced.

Private evidence is under `CrossClassSwitchLab`. Installed ordinary-server
verification is recorded separately from the candidate proof. These checks do
not claim rendered menu acceptance or owner gameplay approval.
