# Editable movement controls — 7 November 2026

Esc > CONTROLS extends the existing original options artwork and English interface. This bounded delivery edits ten actions: forward, backward, left/right strafe, jump/dismount, walk toggle, run lock, face, follow and stick. Each action has two slots. Keyboard modifiers and extra mouse buttons are supported. Escape cancels capture; right-click clears its selected slot. Restore Movement Defaults restores the delivered bridge mapping, not an incomplete RPG/FPS/MMO preset.

The mouse sensitivity slider and inversion checkbox save camera preferences. Existing camera JSON fields survive saves; the new binding map is separate in Saved/DAoCKeyConfiguration.ini. Command-line overrides isolate every automated test from owner preferences. Opening options stops gameplay input, and closing cannot reactivate run lock. The held Shift walk modifier remains fixed. Keys belonging to uneditable interface, quickbar, camera, chat and GM actions remain reserved. Held-movement chords cannot overlap another action on the same physical key; exact one-shot chord reassignment reports its former action.

Reference: original game/ui/keybinds.gd and options_window.gd. Existing bridge defaults remain unchanged. This package does not claim all original settings pages, character-specific key maps, all presets, classic movement style, turn keys, sprint or every original action.

Validation:

- 51 native checks: parsing, defaults, two slots, modifiers, reserved/conflicting keys, malformed persisted maps, saved movement swaps, actual UE input processing, actual input-preprocessor capture, clear/cancel, persistence, camera JSON preservation and screenshot of the real options page.
- 265 established audio/interface checks on the candidate; repeated against installed delivery.
- 53 movement, 9 jump/landing, 35 target-tracking and 65,559 water data checks on the current candidate.
- Real disposable-server ticket purchase, horse movement, original hoof PCM, actual Space dismount, grounded recovery and silence after dismount. Unsupported route purchase retains money/items/mount state. Normal exits and private database restoration verified.
- 76 synthetic receipt checks protect this exact nine-file successor and unchanged previous packages.

The installer previews by default, verifies current evidence/source hashes and the preceding riding receipt, guards normal runtime ports, backs up existing files, verifies copies and restores on failure. Rollback refuses later modifications. No owner database, world map or original content archive is changed. Installed receipts remain immutable; owner gameplay acceptance is recorded separately in the workspace checkpoint.

Owner checks: Esc > CONTROLS, add a second key, move an action to a free key, try a reserved key, cancel capture, clear a slot, restore defaults, change sensitivity/inversion and restart normally. Confirm ordinary movement and Space dismount still work. The owner's prior five gameplay groups were accepted on 7 November; they do not constitute acceptance of this new editable surface.

Next: migrate existing interface/quickbar actions into this same controls surface, with their original dispatch and safe text focus. Avoid unrelated world or visual changes while closing control coverage.
