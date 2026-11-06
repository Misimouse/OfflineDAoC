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

## Restricted central Minotaur activation

The central activation is a separate delivery from the six-table expansion
proposal. `prepare_central_minotaur_activation.py` takes a fresh logical snapshot
of the installed database and prepares only the two original Minotaur starts
(Guardian/Naturalist, Connacht zone 207). It removes race 21 alone from
`disabled_races`. Every existing classic eligibility choice and all other
restrictions remain unchanged: races 16–20 and classes 39/58/62 stay disabled.
The original four male Minotaur careers are Blademaster, Hero, Champion and
Warden. No world population or quest package is imported.

The rules catalog is generated from the accepted joint server source profile.
`verify_character_creation_matrix_real.py --central-minotaur-activation <plan>`
repeats all four creation/saved-reentry cases in the disposable fixture and
requires its eligibility catalog to equal the prepared central catalog exactly.
The normal database and player characters are not used for this protocol test.

`complete_minotaur_godot_resources.py` inventories external glTF dependencies;
the transport model needs eight original texture files, seven previously
absent. The installer verifies these alongside the original modular figure,
four bridge scripts, the narrowly patched race transport metadata, rules and
nine server library copies. It never copies the unrelated dirty network source
wholesale or replaces existing original textures with different content.

`install_central_minotaur_activation.py --apply` refuses stale logical database
state, changed target files, running UE processes and occupied normal server
or bridge ports. SQLite backup, an immediate transaction and full row hashes
protect player progress. Only the two inserted startup identities are excluded
from the preservation comparison; the complete ServerProperty rows must differ
in exactly the intended Value field. On pre-commit failure its own file changes
and transaction are rolled back. Played backups and logs must never enter Git.

Installed receipt: `<bridge>/ExpansionRaceLab/CentralDelivery/MinotaurActivation/installed.json`.
Backup: `<bridge>/Backups/CentralMinotaurActivation_20261106-015451-954381`.
Delivery completed with 25 verified file targets and all previous rows in 125
tables preserved. The other expansion class-data package remains uninstalled.

`verify_central_character_menu.py` separately starts the normal server and the
normal launcher's existing menu probe. It does not enter/create a character,
uses the launcher's credential provider without printing credentials, requests
normal logout and writes `exit` to its own server process. Its live evidence
belongs under `<bridge>/Reports/central_character_menu`, separately from the
disposable four-career proof and owner acceptance.

The installed live menu check passed on 2026-11-06: six existing characters,
76 eligibility choices, no world entry, and normal server/client shutdown.
Its actual rendered selection screen was inspected separately; this is not
owner approval of character appearance or proof of live Minotaur world entry.

The separate installed-resource native world witness subsequently passed with
a disposable Minotaur on the Warden path: actual model 1419, GM protection,
navigation readiness, original bind preserved and normal exit. Run the matrix
with `--central-minotaur-activation <plan> --central-installed-native
--native-world-probe --minotaur-original-start` and the accepted joint candidate.
Evidence stays in `Reports/central_minotaur_world`, leaving the four-career
activation proof intact. The native host mounts only central content and verifies
the installed DLL, catalogs and activation files; the private review asset roots
are not used. This remains a disposable gameplay witness, not a performance,
world-art or owner appearance acceptance.

All four original Minotaur trainer promotions also passed against the central
eligibility profile and accepted joint server build. They promote at level five
and retain the advanced class and received skill lists after saved reentry.
`--minotaur-promotion --central-minotaur-activation <plan>` writes separate
`Reports/central_minotaur_promotion` evidence. Test-only trainers and level
preparation belong to the restored disposable fixture, never the owner's world.

If a closed launcher leaves a server orphan, do not weaken the occupied-port
guard. Its stdin may no longer have an owner. In the observed case, the owner
explicitly authorized termination after a verified SQLite backup. Keep that
exception separate from the routine installer and normal shutdown path.

## Class-data additions delivered separately

`install_central_class_data.py` consumes a fresh conflict-free preview with
every existing table fingerprint. It accepts additions only from the sealed
six-table proposal, refuses occupied server/bridge ports and stale progress,
backs up through SQLite and verifies the full database in one immediate
transaction. Every old row, including every server property, must survive
unchanged. It does not activate races/classes, change inventories or import
quests, regions, NPCs or mobs.

`test_central_class_data.py` exercises synthetic databases: successful six-table
application and idempotency, rollback after an injected partial write, refusal
of changed player progress, and refusal of an occupied bridge port. Its schema
comes from the disposable fixture, with synthetic progress only. SQLite
connections are explicitly closed before Windows temporary-folder cleanup.

The 2026-11-06 central delivery added 254 Spell, 253 LineXSpell, four Ability,
19 SpecXAbility, six ItemTemplate and three StartupLocation rows. Both existing
Minotaur startup rows were preserved. All old rows in 125 tables and all server
properties survived unchanged. Backup:
`<bridge>/Backups/CentralClassData_20261106-022407-975469`.
Receipt: `<bridge>/ExpansionRaceLab/CentralDelivery/installed_class_data.json`.
The normal server/menu then passed again (six existing characters, 76 choices,
no world entry, normal shutdown). Bainshee, Vampiir and Mauler remain disabled;
their data being present is distinct from class activation and playable
acceptance.
