# Original local ground footsteps

Installed 2026-11-06. Thirteen playable model profiles use sixteen byte-identical original WAV files (582,318 bytes). Contacts come directly from the original Godot CharacterSounds helper; an approximation from the retargeted Unreal skeleton was rejected before delivery. Actual animation time and grounded local movement drive playback, with at most one contact per frame. Stationary poses, sitting, death, jumps, previews and NPCs do not produce these footsteps.

This delivery covers dirt ground steps only. Water and swimming triggers remain pending; staging their original resources does not enable them.

Evidence in the local bridge workspace:

- `FootstepAudioLab/OriginalContacts/20261106-134151-290965/verified.json`: original contact extraction for all thirteen models.
- `FootstepAudioLab/NativeAcceptance/20261106-134814-162005/verified.json`: 225 checks, including 149 footstep checks and regressions for doors, options, selection, combat and spells.
- `Reports/footstep_audio_real_protocol/20261106-134813-258946/verified.json`: real disposable server, six actual contacts, six footstep clips, 59,068 consumed footstep PCM bytes, four acknowledged door sounds, closed-door blocking and open-door traversal/return. Normal shutdown and disposable database restoration passed.
- `FootstepAudioLab/InstalledAcceptance/20261106-135626-418569/verified.json`: all 225 checks passed on installed files.
- `FootstepAudioLab/installed.json`: 24 exact files, predecessor hashes, backups and rollback. No production database or player progress changed.

The synthetic receipt-chain suite passes 32 checks. Re-running footstep, door and sound-options installers reports already current without rewriting the installation.

Owner checks remain pending: walk, run, move backwards and strafe; stop and sit; verify steps stop with movement, follow supports and respond to Master/Effects volume. Recheck opening doors and their sounds. Do not use this block as acceptance of water, swimming, mounts, terrain-specific surfaces or NPC footsteps.
