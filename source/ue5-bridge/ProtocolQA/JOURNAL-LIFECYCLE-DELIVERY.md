# Original quest journal lifecycle

This package verifies the installed journal without replacing runtime code or redesigning the quest interface. The owner has deferred quest UI modernization.

The marked protocol database contains no DataQuest records. A private reference therefore contains only original world rows for Evan's Notes (20070), its Evan NPC in Ardee and its two letter templates, read from the installed database without modification. No account or played character is copied. The reference is kept outside Git. Tests insert these rows only after backing up the entire marked disposable database and restore that database afterwards.

Fourteen real checks cover ordinary accounts, an initially empty journal, legitimate NPC whisper acceptance, original step text, actual saved quest state, refusal of another account's abandonment, the original quest-guide response, closing the guide without losing the mission, stale confirmations, original server-confirmed abandonment, saved abandonment, reacceptance with a fresh identity and refusal to reuse the previous journal slot's token. This is a journal/guide/abandonment test; it does not claim completion or reward testing for every quest.

Twenty-nine existing state checks cover ordering without index renumbering, literal text/goals, original zero-based wire removal, pending acknowledgements, timeouts, replaced quests, malformed indices, guide routing, late response suppression and session isolation. Eighty-three installed native checks include actual journal controls, selection, removal confirmation, original guide presentation and retained window position.

All normal runtime files and server libraries remain unchanged. Owner gameplay acceptance is pending. Review with an ordinary eligible character: accept a real available mission, open the journal, read the steps and guide, close the guide, and abandon only a disposable test mission. Quest UI modernization remains a future separate block.
