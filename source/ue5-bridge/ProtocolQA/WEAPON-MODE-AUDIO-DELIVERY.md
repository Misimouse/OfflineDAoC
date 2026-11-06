# Original local weapon draw and sheathe audio

The bridge emits the original weapon `activate` and `deactivate` sounds only
after a real server attack-mode acknowledgement. Input requests alone do not
produce sound. This extends the installed combat audio stream and uses its
unchanged native player and original resource catalog.

`weapon_mode_audio_state.gd` resolves the actual equipped model in the active
one-hand, two-hand or ranged slot. Sheathing retains the model previously
drawn, even if the selected slot has changed. Duplicate acknowledgements are
silent. Login, region changes, logout and death clear the local state without
inventing a sheathe sound. Empty equipment remains silent. Inventory, combat
rules and server authority are unchanged. Remote-player draw/sheathe and
ambient/door audio are outside this delivery.

## Verification

- Fifteen isolated producer checks pass, including duplicate acknowledgement,
  slot changes, death, empty equipment and preservation of input state.
- An isolated real server fight emits both draw and sheathe alongside actual
  combat events. The installed-equivalent UE binary consumes all seven events
  (184,930 PCM bytes), with no unresolved references or invalid resources.
  Hit/miss outcomes can change the number of events; the assertion compares
  actual emitted events rather than requiring an invented fixed hit count.
- The fixture disengages before normal logout and restores its database and
  server. No owner character is used for this fight.
- The normal character menu opens with six existing characters and 83 choices,
  without entering the world, and shuts down normally.
- All three audio installers and class activation report already current.
  Ten synthetic receipt-chain checks pass, including rejected tampering of
  the successor gateway, native hash, new module and old spell resources.

`install_weapon_mode_audio.py` installs exactly two bridge scripts with backup,
hash guards, exclusive normal-port checks and rollback. It changes neither the
native binary nor the database. Its immutable receipt binds the accepted
combat delivery and its playback proof. Subsequent native checks use fresh
report directories, and sealed audio build roots refuse rebuilding, so old
accepted evidence cannot be silently overwritten.

Private evidence lives under `WeaponModeAudioLab` and
`Reports/weapon_mode_audio_real_protocol`. Generated sounds, logs, backups and
played data are not committed. Automated PCM consumption does not establish
subjective listening or volume acceptance. Listen in game through the normal
`INICIAR-ARDEE-GM.cmd` launcher: draw and sheathe different equipped weapons,
then check death, repeated toggles and ordinary combat.
