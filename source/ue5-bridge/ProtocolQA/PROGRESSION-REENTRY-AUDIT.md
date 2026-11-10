# Saved progression and same-connection character reentry

`DAOC_PROGRESSION_TRAINING=return` passes27 ordinary-server checks, including
the installed affordability scenario. It earns level2 /64 XP through melee,
trains Regrowth2 and saves the original heal on a selected quickbar page.

The original `/quit` reaches character selection after server-confirmed saving,
without closing the bridge connection. Old world entities, selection and cast
state are cleared. The roster displays the earned level. Reentering that character
produces a fresh player generation and current server skill list; the earned XP,
trained rank, remaining points, selected page and valid saved heal are restored.
The saved shortcut resolves and accepts its original use request after reentry.
Final normal logout preserves the same server data.

Private DB/server libraries are restored, both ordinary clients and the server
exit normally, and normal runtime hashes remain unchanged. No deployment was
needed. These are protocol/state checks, not rendered character-menu acceptance
or another full spell-effect test. The prior casting package separately covers
actual healing and new buff application.

Private proof: `ProgressionReentryLab`. The next bounded scenario switches class
within the same ordinary account and checks that previous skill identities and
saved shortcuts cannot act as the new character's abilities.
