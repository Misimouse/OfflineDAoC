# Original options art and persistent sound controls

Delivered 2026-11-06. Escape opens the sound options after the existing window-close handling. Escape or CLOSE dismisses it without logging out. CHARACTER SELECT requests the existing `/quit` path; QUIT requests the normal saved logout.

The original converted `options.png` is copied byte for byte. Master and sound-effects sliders persist in `Client/Saved/DAoCBridgeAudio.ini` and update already-playing voices. Opening the menu blocks world pointer and gameplay input without pausing the server. This delivers the sound page only; graphics, key bindings, music and ambience options are not claimed as migrated.

Private candidate and installed-client acceptance each passed 61 checks: 17 options/persistence/live PCM checks, 15 body-selection checks, 14 combat-audio checks and 15 spell-audio checks. The options capture uses the actual Slate widget, with a nonblack-pixel assertion. All test settings use private INI files; owner preferences and characters are untouched. No server is required for these native checks.

Evidence: `OptionsAudioLab/Acceptance/20261106-114325-547854/verified.json` and `OptionsAudioLab/InstalledAcceptance/20261106-115359-307239/verified.json` in the bridge workspace. Installer records ten exact files, seven backups and three additions in `OptionsAudioLab/installed.json`. The receipt chain admits this explicit successor to body selection; historical proofs remain immutable. Rollback preflights current and backup hashes, and preserves user audio preferences.

Owner checks remain: open Escape in the world, adjust both volumes while hearing combat/spells, close without leaving, reopen and restart to verify persistence, then check CHARACTER SELECT and QUIT. Automated playback is separate from the owner's listening check.
