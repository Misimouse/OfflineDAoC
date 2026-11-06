# Original server-requested SoundEffect audio

Installed 2026-11-06. Packet 0xC9 now reaches a separate bounded native event queue. The catalog contains 28 original event rows, covering all eleven fixed sound IDs called by the checked-in server source. Original ADPCM files use the existing upstream decoder, with original sample rate, channels and sample count verified; other WAV files remain byte-identical. No substitute sounds were introduced.

Quest notifications and other zero-zone/zero-radius events play without distance attenuation. Placed events use the packet radius measured from the actual player, independently of camera distance. The current bridge accepts placed audio only in its rendered Connacht zone. Unknown IDs, malformed packets and stale events stay quiet. Sequence IDs prevent snapshot replay; logout/zone changes clear retained events. The normal Master/Effects controls apply to these voices.

Evidence in the local bridge workspace:

- `Reports/server_sound_audio/coverage.json` and `ServerSoundAudioLab/resources.json`: source references, original hashes and documented ADPCM decoding.
- `ServerSoundAudioLab/StateTest/20261106-143936-809225/verified.json`: 20 packet dispatch checks.
- `ServerSoundAudioLab/NativeAcceptance/20261106-142603-228828/verified.json`: 265 checks, including 40 event-audio checks and all prior footstep/door/options/selection/combat/spell regressions.
- `Reports/server_sound_audio_real_protocol/20261106-143641-943161/verified.json`: existing GM `/cast sound` commands produce actual server packets 7, 11 and 12, three native event clips and 360,448 consumed event PCM bytes after preceding door voices finish. Normal shutdown and disposable database restoration passed.
- `ServerSoundAudioLab/InstalledAcceptance/20261106-144217-443806/verified.json`: all 265 checks passed on installed resources.
- `ServerSoundAudioLab/installed.json`: 38 exact files, guarded predecessor hashes, backup and rollback; no production database changes.

The first real-protocol attempt retained under `20261106-142816-096205` failed because the transport whitelist omitted the new snapshot field. That omission was fixed and the complete test repeated successfully; the failed proof is preserved.

Receipt-chain suite: 37 synthetic checks passed. Re-running this installer and prior footstep/door installers reports already current without rewriting files.

Owner listening remains pending. With GM enabled, use the existing commands `/cast sound 7`, `/cast sound 11` and `/cast sound 12`; compare at low Master/Effects levels, then mute Effects. Ordinary quest accept/completion notifications use this same packet path. This does not certify quest UI migration, ambient loops, music, arbitrary GM sound IDs beyond the staged catalog, swimming or NPC footsteps.
