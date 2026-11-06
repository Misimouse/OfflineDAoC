# Server-confirmed original door sounds

Installed 2026-11-06: 17 original sound-set definitions, 25 byte-identical original WAV files, a separate catalog and acknowledged open/close triggers. The sound is anchored to a loaded door group, so two leaves do not play twice. Zero flags, unknown IDs/sets, empty slots, repeated packets and initial hydration stay silent. No default based on zone is invented. Two missing original destroyed-bridge structures remain unresolved and silent.

Evidence in the local bridge workspace:

- `DoorAudioLab/StateTest/verified.json`: 16 trigger checks.
- `DoorAudioLab/NativeAcceptance/20261106-120825-840069/verified.json`: 76 checks across doors, options, body selection, combat and spells.
- `Reports/door_audio_real_protocol/20261106-121935-050989/verified.json`: actual disposable-server open/close acknowledgements forwarded into UE5, original PCM consumed, no duplicate opening, normal shutdown and disposable database restoration.
- `DoorAudioLab/InstalledAcceptance/20261106-122528-930673/verified.json`: all 76 checks passed using installed resources.
- `DoorAudioLab/installed.json`: 34 exact files, guarded predecessor chain and backups. No production database, player progress, door geometry, collision code or original sound library is changed.

Additional traversal regression is **not accepted**: `Reports/door_audio_real_protocol/20261106-123035-685570/verified.json` failed its inside-door collision witness. The current cleaned map's test trajectory reached 2.79 m and was deflected sideways instead of crossing the 3.17 m doorway plane. Real opening/closing and their sounds passed separately. This failure remains visible and requires a dedicated current-map collision/fixture investigation; it is not reported as a completed traversal test. The old successful crossing proof used the earlier map/character and does not certify the current one.

Owner checks: open both Ardee door types at close range, hear opening and automatic server closing, repeat clicks without duplicated sound, then verify the route through each doorway. Master/Effects volume controls should affect these sounds too. Owner listening and traversal acceptance remain pending.

## Traversal follow-up

The failed witness above was a test startup race: movement began while streamed structure collision was still absent. The private relay now withholds the local test pawn until terrain, both door groups and all eleven structure colliders report ready. No collision geometry or movement rule was changed.

`Reports/door_audio_real_protocol/20261106-125700-249393/verified.json` passed on the same native DLL as the installed client: closed leaves block outside and inside, opening permits crossing beyond six metres, return reaches the starting point, four actual server transitions produce four native clips and 245,500 consumed PCM bytes, then client/server close normally and the disposable database is restored. Historical failures remain intact. This supersedes the automatic traversal limitation above; owner listening and in-game acceptance still remain pending.
