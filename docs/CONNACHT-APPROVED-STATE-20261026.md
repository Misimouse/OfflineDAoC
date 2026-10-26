# Connacht approved code checkpoint — 26 October 2026

This checkpoint preserves the reusable source supporting the owner's approved Connacht terrain, vegetation and forest work. It is a source-control checkpoint, not a release or deployment to the normal client.

## Included source

- Extend native-distribution terrain overrides from the four-patch pilot to all64 Connacht patches, keeping source/hash guards and restoration.
- Deterministic vegetation cells with numeric road/water/terrain masks, worker generation, prefetch and bounded cache. Preserve the approved vegetation catalogue and insect model factory.
- Guard removal of native ground clutter behind an explicitly configured private LAB flag, including streamed/revisited zones. Normal-client behavior remains unchanged when the flag is absent.
- Preserve the player's MSAA choice while maintaining the forest's temporal smoothing across graphics-setting changes. This does not claim the remaining in-game canopy shimmer is resolved.
- Allow disabling the review-only giant mushroom while retaining approved small mushrooms.

## Owner approvals recorded in the conversation

Ardee, water, ground/lawns/sand, small mushrooms and bindstone; forest appearance and variants; Tir na Nog exterior marble; Elf Bridge and Tower; Mud Pile; fortress doors and Hibernian banner; Darkness Falls exterior entrance; horse cart and Meath; Druim Ligen platform/roof/ivy; Parthanan straw; Cluricaun including its fire; mountain appearance; Siabra camp apart from the subsequent request to share Cluricaun fire. Approval is visual feedback by the owner, distinct from automated test results.

## Resource package and normal source builds

The owner also approved Parthanan canvas/fence, Muire and the final balanced owl/beast effects on 26 October, and requested that the resources be included in Git. The versioned package under `source/new-client/approved/connacht-20261026` supersedes the earlier code-only checkpoint plan. See its README for installation, integrity verification, rollback, base-content prerequisites and provenance.

The source build installs the approved resources automatically. The normal zone viewer then uses the same approved profile families without a private LAB login or absolute developer paths. The existing LAB is left intact and explicitly avoids the additional source-build binding. Downloading the repository still requires the original converted base content, as before; it does not supply a complete original DAoC installation.

No new water/shore/fish changes are included in this checkpoint. Historical experiments retained as resource/source dependencies are not new owner approvals. Local test outputs, accounts, logs and caches remain excluded.

## Validation

The included controllers were loaded by the isolated Connacht/capital reviews used during the work, with exact restoration checks; a dedicated parse/load check covers the nine source files in this checkpoint. No game server is started for this check. Render reviews do not replace in-game performance or flicker validation. The live LAB entry, active profile pointers and original zone data are unchanged by this commit. The installer is checked independently from the live LAB and normal installed game.
