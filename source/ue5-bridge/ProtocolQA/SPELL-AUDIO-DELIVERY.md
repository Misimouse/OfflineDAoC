# Spell audio delivery

The native UE client now resolves original spell sound structures instead of
silently rendering their visuals. This is spell audio only: creature voices,
weapons, footsteps, doors, music and region ambience remain separate blocks.

## Sources and behavior

`prepare_spell_audio_resources.py` uses the existing Godot `build_sounds.py`
decoder and the original client `cc_sounds`, `cc_spells`, `cc_groups` and
`cc_queues` tables. It stages 184 original PCM16 WAVs (20,674,884 bytes), 69
sound sets and a catalog in a separate `OriginalAudio_v01` directory. Original
client assets and tables are unchanged.

Three exact aliases reconcile the original tables' `MagicMissile` spelling
with the same original phase WAVs named `MagicMissle`. No other spell's sound
is substituted. Effect 5921 references sound set 332, which has no original
table row; that known gap remains silent.

The producer preserves the server's silent-pulse flag and distinguishes
interruption from actor removal/death. UE resolves gather, cast, travel, hit,
resisted and fizzle structures, including original groups, queues, volume,
pitch, delay and distance ranges. Release or interruption stops gathering;
session cleanup stops every voice and pending clip. Repeated snapshots,
old events and duplicated group-target release bursts do not stack audio.
The renderer caps voices at 48, delayed clips at 256 and decoded PCM at 32 MiB.

## Evidence

Evidence is private under `DAoC-Godot-UE5-Bridge/SpellAudioLab`; played data,
logs, converted assets and backups are not committed.

- `verify_spell_audio_state.py`: isolated Godot metadata checks, no server.
- `verify_spell_audio_native.py`: 15 native checks with real audio-engine PCM
  consumption, quiet pulses, alias resolution, duplicate suppression,
  interruption, stale events, missing original set and cleanup.
- `verify_starting_spells_real.py --audio-native-candidate`: disposable real
  server Bainshee cycle; authentic spell packets drive audio consumption,
  body/portrait transformation and timed equipment/appearance recovery.
  Server, fixture DB and catalogs are restored and shut down normally.
- `verify_central_expansion_native.py --audio-candidate`: character/material
  regression, 72 creation and 78 customization checks. The full 4,263-check
  appearance suite retains its single known source-empty Minotaur horn
  morph limitation; it is explicitly not recorded as a full pass.
- `verify_spell_audio_native.py --installed`: the same 15 audio checks resolve
  the installed catalog through the default plugin path, with no private
  sound-catalog override.
- The normal character-menu smoke checks existing characters and choices
  without entering the world, then closes the server normally.

Automated consumption proves that audio reaches the engine, not subjective
owner hearing/volume acceptance. The owner still needs to listen in game.
Filtered Bainshee witness captures are actor checks, not scenery/FPS approval.

## Installation and provenance

`install_spell_audio.py` validates source/build/resource/protocol/regression
hashes, refuses running UE clients and occupied normal ports, previews all
193 file targets, backs up replacements and rolls back on failure. It copies
the tested DLL/modules, five reproducible native source files, the additive
Godot event metadata script, and the new sound directory. No DB, eligibility,
world population, original models or shared art is changed.

`installed.json` records before/after hashes, evidence hashes and backup paths.
Re-running the installer verifies the installed hashes without copying again.
Historical character-form proofs remain immutable and pin their original
DLL. The later audio receipt and its new regression/protocol evidence record
the successor client; old proofs are not relabeled as current.

Normal launcher: `DAoC-Godot-UE5-Bridge/INICIAR-ARDEE-GM.cmd`.
Owner checks: cast an audible spell, interrupt its preparation, repeat a buff,
leave/re-enter normally, and check that preparation sound stops on release,
interruption and logout. Existing spell visuals and equipment recovery must
remain intact.
