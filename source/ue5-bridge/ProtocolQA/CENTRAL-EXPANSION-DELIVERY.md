# Central expansion client delivery

This stage unifies validated character resources with the central client. It
does not replace the world database, activate races/classes, or import population.

## Preserve existing visual work

The private review's global skin/hair materials differ from the central visual
calibration. Copying its whole appearance catalog would replace that calibration
for existing races. The merged catalog retains central `materials` and
`surface_materials`, and places optional `materials.skin`/`materials.hair` under
the new figure entries 1075, 1087 and 1419. Runtime resolution is per material:
an omitted figure field inherits the central default. Existing catalogs remain
compatible. The optional override applies to the actual head/body/hair parts.

`prepare_central_expansion_delivery.py` adds model, equipment, appearance, original
transport-task and lore records. Existing natural identities must match exactly;
conflicts abort preparation. It indexes whole missing asset roots, including
dependencies embedded in UE assets, rather than just direct JSON paths. The
five generated catalogs retain all old rows. Current globals stay unchanged.

## Native acceptance and installation

`build_central_delivery_native.py` builds `CentralDeliveryHost` separately from
the normal plugin, `SharLobbyHost` and `FormLiveHost`. Earlier proof binaries
remain unchanged. `verify_central_expansion_native.py` requires actual material
parents to match every figure's expected override/default. It also tests a
partial override that must inherit central hair while retaining figure skin.

The native appearance suite has 4,263 checks. Its original source-empty Minotaur
Horn Size render-weight failure remains explicitly present; this delivery does
not claim full appearance acceptance or invent a horn morph. The material checks
introduce no additional failure. Original creation/customization checks pass
72/78 checks, with real screenshots requiring visual inspection.

`install_central_expansion_client.py` defaults to a dry run. With `--apply` it
requires stopped UE editors/game, matching engine BuildId, unchanged central
inputs, pinned successful native evidence and sufficient space. It backs up
the five catalogs plus plugin library/module manifest, adds only absent asset
files, verifies hashes, and rolls back its writes on failure. Existing asset
content must match and is never overwritten. It does not change server libraries,
database records or activation flags.

`sync_central_expansion_sources.py` additionally compares canonical plugin sources
with the source payload actually compiled by the accepted host. Changed installed
sources are backed up and synchronized so subsequent central builds retain the
same behavior. Its rollback records live beside the client backup under `Sources`.

After installation, repeat `verify_central_expansion_native.py --installed`.
That host mounts only central plugin/project content and uses the actual installed
catalogs and library; private art fallback is unavailable. Results are separate
under `CentralDelivery/NativeInstalledAcceptance`. This verifies the delivered
resources, not live world entry or server class activation.

## Class-data preparation remains separate

`prepare_central_expansion_data.py` compares the accepted six-table class package
with a disposable read-only main+WAL snapshot. It reports natural-key conflicts
and allocates association/startup surrogate IDs without replacing existing rows.
When conflict-free, it applies the proposal to an in-memory copy and fingerprints
every existing table to verify preservation, including player progress.

The 2026-11-06 preview is conflict-free: 254 spells, 253 associations, four
abilities, 19 career associations, six item templates and five starts are absent.
All existing rows in 125 installed tables survive the in-memory application.
This is **not** an installation or race/class activation. Catacombs world spawns,
dungeons and quests remain deferred until more world is ready, per owner request.

## Installed evidence, 2026-11-06

Client receipt: `<bridge>/ExpansionRaceLab/CentralDelivery/installed_client.json`.
3,485 absent files were copied (4,162 indexed assets; approximately 1.51 GB).
Five plugin source files were synchronized. Central creation/customization and
material inheritance passed again using installed resources only. Both rendered
screens were visually inspected by Codex; owner visual acceptance is separate.

Backup: `<bridge>/Backups/CentralExpansionClient_20261106-002505-012857`.
`rollback.json` lists old catalogs/libraries and newly added files;
`Sources/rollback.json` lists the synchronized source backups. Preserve later
edits when reverting: verify installed receipt hashes before restoring a file or
removing a newly added asset. No recursive cleanup of resource roots is needed.
