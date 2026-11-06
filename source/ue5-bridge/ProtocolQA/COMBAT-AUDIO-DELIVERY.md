# Original combat audio

Follow-up: local server-confirmed draw/sheathe triggers are now delivered in
[WEAPON-MODE-AUDIO-DELIVERY.md](WEAPON-MODE-AUDIO-DELIVERY.md). The trigger
limitation below describes this original combat delivery before that follow-up.

The bridge now publishes a separate `combat_audio` stream from actual server
combat/death packets. UE uses the same bounded PCM playback engine as spell
audio, with a separate original creature/weapon catalog. The world, HP,
inventory, combat power, damage and AI remain server-authoritative.

## Original references

`audit_combat_audio_coverage.py` compares the current native model IDs with
original `gamedata.mpk/monsters.csv`, `objects.csv` and the `cc_*` sound tables.
Dispatch follows Godot `server_world.gd:_combat_sounds`, checked against DOL's
`PacketLib186.cs` combat packet fields and `SpellHandler.cs` damage dispatch.

The current audit resolves 27 creature sets and all 25 original weapon sets:
498 named references, 332 unique original PCM16 WAVs, 14,339,792 bytes. There
are no missing references, structures, files or cycles in this scope. Six
original model rows intentionally have no sound set. Synthetic model 0 has
no original row and receives no invented creature sound.

`prepare_combat_audio_resources.py` creates `OriginalCombatAudio_v01` under
a separate staging root. It retains original groups, queues, offsets,
volume/pitch ranges and 1,405 original weapon-model sound mappings. Original
client tables/files and the installed spell-audio directory are unchanged.
When the native model catalog grows, rerun this resource inventory/export;
there are no NPC-name or map-location sound overrides.

## Dispatch and playback

- Weapon swing, ordinary/style impact, parry, block and unarmed attacks use
  the original weapon/creature sheet rules.
- Damage fraction selects light/medium pain/impact. Pain voices are limited
  to one per character per 700 ms; fatal hits and the following death packet
  produce one death voice.
- Spell damage, including masked result `0x94`, never plays a weapon swing.
  Bow preparation cannot invent damage, pain or death.
- Death sound positions remain anchored after an actor identity is removed.
  Anchors use the same DAoC-to-UE origin as actor positions. Cache keys include
  the library root so identical filenames cannot cross-contaminate catalogs.
- Repeated snapshots, stale events, empty original slots, actor ID reuse and
  session cleanup have explicit checks. No source sound is substituted.

This block excludes footsteps, idle cries, music, zone ambience and door
sounds. Draw/sheathe table data is exported, but that additional trigger path
is not yet connected or accepted by this block.

## Verification and delivery

Private evidence stays under `CombatAudioLab` and
`Reports/combat_audio_real_protocol`; no logs, backups or played data ship.

- Isolated Godot dispatch: 22 checks, with authority preservation.
- Native combat playback: 14 checks and actual PCM consumption, including
  original timing offsets and post-removal death audio.
- Spell regression: the original 15 playback checks still pass.
- Actual isolated server: ordinary level-50 Vampiir melee emits five original
  swing/impact/vocal events; UE consumes their PCM with zero missing/invalid
  references. Original power starts at 0 and reaches 5 through real damage.
  The fixture disengages before normal logout; DB and server are restored.
- Character/material regression: 72 creation, 78 customization checks. The
  existing source-empty Minotaur horn morph failure remains explicitly open
  in the 4,263-check appearance suite; it is not recorded as a full pass.

The test observer waits until its native snapshot sequence catches up after
UE startup before starting combat. It does not replay old sounds to turn a
missed observation into a passing real-protocol test.

`install_combat_audio.py` validates these proofs and source/resource hashes,
previews 343 targets, refuses running clients/occupied normal ports, backs
up replacements and rolls back file writes on failure. It changes no DB,
eligibility rules, spawn population or original art. The new receipt records
its exact predecessor DLL and the immutable spell-audio and Minotaur receipts.
`central_activation_receipts.py` accepts precisely that recorded gateway
successor and verifies both the new files and unchanged spell-audio files.
Five synthetic chain checks reject tampered predecessor/target hashes.

`verify_combat_audio_native.py --installed` repeats combat and spell checks
using default installed resource paths. Automated engine consumption is not
subjective hearing/volume acceptance; the owner should listen in game using
`INICIAR-ARDEE-GM.cmd`.
