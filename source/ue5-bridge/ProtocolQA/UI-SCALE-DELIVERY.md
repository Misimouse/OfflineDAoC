# Original interface scale

This delivery ports the existing Godot Options / Interface / UI Scale preference into the native client. It is a client-only package; it changes neither server rules nor the played database.

The original range is 60–160%, in 5% steps. Dragging previews the percentage and applies on release, so the slider does not move under the pointer. Keyboard changes apply immediately. Closing during an unfinished drag cancels that preview. Save failure retains the previously applied size.

The default preserves the established native interface size at ordinary resolutions. Existing edge-based window placement reflows after a change. The largest existing window is kept within the viewport, so the effective size may be limited on smaller screens. This limit is explained in the Interface page. The original options artwork is retained and all new text is English.

Settings use Saved/DAoCBridgeInterface.ini, with version checking, finite range validation and full float round-trip precision. Unattended native tests use an explicit private settings file; they do not read or write the owner's preference.

## Verification

- `verify_ui_scale_native.py`: two fresh native processes, 218 checks each. Exercises the actual Slate slider and capture-end callback, all 21 original steps, seven viewport sizes, malformed files, save failure, close cancellation, default restoration, reflow and absence of gameplay requests. Captures both ordinary and enlarged Options pages for visual review.
- `verify_ui_scale_regressions.py`: scale, hover descriptions, item handover, emblem, guild, display, editable controls, movement, landing, tracking, water and the seven existing audio/UI cases. Every report is tied to the candidate build hash.
- `test_audio_receipt_chain.py`: synthetic predecessor, exact target, backup identity and tampering guards. No played data is used.
- `install_ui_scale.py`: requires the above evidence and replaces exactly ten native files, with bounded backups and rollback. Original Godot and server files remain as installed by their preceding deliveries.

Owner gameplay review remains separate from automated acceptance. After installation, open Esc → Interface, drag UI Scale, release it, close/reopen Options and restart the game. Check a few inventory/chat/quickbar windows at the preferred resolution, then use Restore Default Size if desired.

Installed on 2026-11-08 after all 12 candidate regression packages passed, including 265 audio/UI checks. The installed client passed the same 436 scale checks. The 197 synthetic receipt guards passed. Installation replaced ten native files with an exact backup; the played database and server remained unchanged. Owner review is still pending.

Auto loot, bot visibility, chat filtering and window restoration from the other original Interface/Options sections are separate packages. This delivery does not claim the complete Options window is migrated.
