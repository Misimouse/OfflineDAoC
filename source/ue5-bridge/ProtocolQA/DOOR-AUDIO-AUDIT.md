# Original door audio: audit and staged resources

This is preparation only. Door sound is not installed or accepted yet.
The normal bridge, native binary, original client and database are unchanged.

`audit_door_audio_coverage.py --workspace ... --install ... --stage` reads the
original `cc_doors`, sound and structure tables. It records source hashes and
stages resolved original PCM in a separate `DoorAudioLab/OriginalDoorAudio_v01`.
It does not overwrite the accepted spell/combat catalogs or their evidence.

The current original client declares 17 door sets. Twenty-five original WAVs
resolve (4,255,748 source bytes), with no missing files, cycles or loop support
requirements. Two authored names do not resolve: `s_destroyedbridge1` and
`s_destroyedbridge2`. Other rows reference similarly named WAV files through
different sound names; no alias or substitute is inferred. Sets 10 and 11
remain explicitly unavailable. `passed` means the audit/staging completed;
`coverage_complete` remains false. Ordinary door set 1 resolves both events.

The current collision catalog has door groups 207033603 and 207033701. Native
door interaction and animation already exist. The missing audio connections
are the decoded packet flag, currently discarded by `live_gateway.gd`, and
native playback when an authoritative door state changes.

## Authoritative reference and remaining acceptance

`DaocClient.cs` decodes packet 0x99 as door ID, open state and sound flag.
`PacketLib168.SendDoorState` applies the server's default sound only to
unflagged, non-keep, above-ground doors outside Trials of Atlantis. The bridge
must honor a zero flag as silent rather than reproduce a broader zone-based
guess. Godot's original zone-door code is useful for grouping and attenuation,
but its zone default is not a substitute for the transmitted flag.

Before delivery, the next candidate must prove:

- Original open/close playback at the loaded door group's position, once for
  a double door and once per actual state transition.
- Silence for repeated snapshots, flag zero, unknown IDs and missing slots.
- Quiet initial state hydration when joining beside an already-open door;
  no fabricated sound caused only by loading or reconnecting.
- A real server open, crossing, server close and return, preserving collision
  and authority, with actual PCM consumption in a fresh native candidate.
- Existing spell/combat/draw audio regression and a guarded successor install.

No owner character should be used for the protocol acceptance fixture. Old
sealed audio hosts and proofs must remain intact. Listening and volume
acceptance remain a separate owner check after a tested delivery exists.
