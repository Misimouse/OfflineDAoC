# Private Minotaur review

This package does not activate expansion races on the normal installation.
It uses a separate database, server ports 10361/10461, bridge port 19747,
Godot profile and native plugin. Never publish its database, logs or private
account configuration.

The accepted path includes four male Hibernian careers: Blademaster, Hero,
Champion and Warden. Real protocol checks cover creation, exact saved appearance
bytes, original trainer promotion at level 5 and saved reentry. Native checks
cover 31 outfit/cape sections, equipment visibility, original animation,
inventory preview and the original creation/customization interface.

The owner review is exported only after a successful promotion matrix has
stopped its client and server normally. `--review-output` refuses to overwrite
an existing review copy. The disposable source fixture is restored afterward.
The review has four existing level 5 characters with GM account access.
The initial export disables additional creation conservatively. After the
separate original-start protocol matrix passes, `enable_minotaur_review_creation.py`
replaces that guard with a Minotaur-only creation scope, with a rollback copy.
Other races remain outside this review's creation scope until their native
entry and starter equipment are integrated. Existing review characters and
their database are preserved.

The original Minotaur coordinates (340874, 467094, 5200 in region 200) are inside
Connacht zone 207, whose bounds are x=35..43 and y=51..59 in 8192-unit cells.
The earlier claim that these starts required another native zone was incorrect.
`--minotaur-original-start` verifies all four careers without fixture relocation,
including world position, original bind, saved appearance, skills and reentry.

`launch_minotaur_review.py` starts and closes this separate server automatically.
`--smoke` checks its live character menu; `--smoke-world` checks connection,
character identity, Ardee map and navigation before normal automatic logout.
Without either switch, it opens the interactive review client.

Remaining limitations:

- Original Horn Size targets FM1/FM2 contain zero source vertex deltas.
  The UI value is saved, but no horn-size deformation is claimed. The ten
  original horn/hair models are separate working appearance choices.
- Minotaur helmet assemblies and full equipment coverage remain separate checks.
- Native screenshots and automated checks do not constitute owner visual approval.

## Original realm and helmet audit

`audit_minotaur_sources.py --client ORIGINAL_CLIENT --official-archive OFFICIAL_GAME_DATA
--output PRIVATE_REPORT` compares the installed and official catalogue tables
without modifying either archive. The official catalogue probe does not need
the item meshes; the installed original client must contain all ten item NIFs.

The original realm identities are Albion monnifs 863 / figure 61, Midgard
867 / 62 and Hibernia 868 / 63. Their horn choices, cape parts and animation
sets differ. Shared body part IDs do not authorize substituting one realm's
complete appearance for another. Only the Hibernian variant is in this review.

Both inspected catalogues contain ten `_min_m` mask/hat items. None is referenced
by the objects table's twelve Catacombs helmet columns. The masks instead use
the original `NoArmor Helm=1` path: column 2 is the item ID and column 12 is
the specific helmet skin. This establishes thirteen mask appearances from nine
original NIFs, including four decorated variants. The Yule hat still has no
confirmed equipment mapping; the pumpkin is an effect path, outside this conversion.

`prepare_minotaur_helmet_sources.py --client ORIGINAL_CLIENT --lab PRIVATE_LAB`
converts only those explicit mask references. It copies original textures
without upscaling, preserves variant skins and writes no active catalogue.
The source audit compares these references against the official catalogue too.
Geometry checks and native imports are separate from native visual acceptance.

The three figures have no full-helmet slot 9. The official
[1.125 notes](https://www.darkageofcamelot.com/1125-live-patch-notes/)
identify the Minotaur-specific masks as the visible helmet exception. Ordinary
helmet equipment need not display a mesh on this race. Numeric matches in
unrelated texture, effect or armour columns are different ID namespaces and
must not become helmet mappings. Do not force another race's helmet onto it.

## Joint expansion regression candidate

`build_overlay_server_candidate.py` accepts `--vampiir-creation` together with
`--minotaur-reference` for a separate joint candidate. It composes both changes
in a new GlobalConstants file while preserving the isolated Minotaur variant
and its manifest. Normal source files and installed server libraries are not
replaced. Bainshee and Shar rules remain those of the existing source.

Run the real creation matrices with `--combined-expansions` and the joint
`--candidate-build`; this writes evidence under `Reports/combined_expansions`
without replacing the earlier independent acceptance reports. The combined
menu must retain 3 female Bainshee, 6 Vampiir, 12 Shar and 4 male Minotaur choices.
The Minotaur run additionally uses `--minotaur-original-start`.

`verify_combined_expansions.py --workspace PRIVATE_WORKSPACE` requires all
twenty-three real creation/appearance/skill/saved-return cases (including ten
Shar starter-equipment runs), unchanged normal
sources, matching build hashes, restored disposable databases and normal
shutdown. It also checks native creation/customization and equipment evidence.
The broader native facial-weight suite still reports the source-empty
Minotaur horn target limitation; its failure is retained explicitly in the
joint seal. This is not deployment approval or joint live-world acceptance.
Mauler remains outside this package.

For live native witnesses, add `--native-world-probe` to the combined
Minotaur original-start, Bainshee or Vampiir-Shar matrix. Each focuses on one
creation and reentry; the full twenty-three-case matrices remain independently
sealed. Witness accounts are disposable GMs and must receive server confirmation
of protection. The Minotaur QA initial spawn matches its original DOL start
exactly, avoiding an unnecessary GM jump. The harness
then enters that disposable character and closes its protocol observer socket.
The disposable transport first explicitly releases its observer peer; this
test-only command is injected into the QA copy, never the production gateway.
Unreal then takes the bridge's single peer, renders the actual Connacht map,
records connected/navigation evidence and a screenshot, and logs out normally.
Only then may the harness restore its disposable fixture. Reports go to a
separate `_world` directories for each matrix. Bainshee and Vampiir witnesses
are level-one base classes, not proof of their advanced abilities.

`verify_combined_expansions.py --include-native-world` additionally verifies
all three witnesses, confirmed GM protection, unchanged binds, normal shutdown
and absence of reported missing local weapon models/bones. Original bind
acceptance applies to Minotaur; the Shar fixture relocation remains explicitly
recorded. Screenshots require visual review. Advanced abilities, transformations
and Horn Size are separate acceptance.

The swatch export reuses the original Godot menu's sampling functions in a
private adapter. Adding color picker controls does not modify rendered materials,
textures or morph geometry. Shar and Vampiir native regression cases run against
the same private plugin library.

Joint advanced protocol acceptance uses `verify_starting_spells_real.py
--combined-expansions --candidate-build PRIVATE_CANDIDATE --server-source SOURCE`.
Run the original Bainshee trainer promotion, Shar-female Vampiir promotion,
and Bainshee form cycles for races 9, 11 and 12, with their explicit DOL data
proposals. Evidence is separate under `Reports/combined_expansions/starting_spells`.
The Bainshee promotion also checks the advanced class and full spell list after
saved reentry. Form cycles require the original 30-second server timer, unchanged
inventory and restoration of the selected appearance; these are protocol tests,
not a live Unreal transformation rendering claim. `verify_combined_expansions.py
--include-advanced-protocol` requires all five reports from the same joint build,
including restored QA data and clean shutdown. Missing Bainshee promotion gift
`bainshee_item` is recorded; the pinned public reference contains no matching
item. Do not manufacture a replacement as part of this acceptance.

Live native form witnesses add `--native-form-probe` to each combined Bainshee
form-cycle run. The read-only relay uses the separate private `FormLiveHost`,
current review catalogues, and full original UI snapshots. The opt-in
`-DaocBridgeVisualProbe` opens the actual inventory and reports the meshes
assigned to the world and portrait components; it does not change model,
equipment or spell state. Reports `native_before.json`, `native_transformed.json`
and `native_restored.json` must show the correct original form asset, zero worn
weapon components during transformation, and restoration of the actual initial
body, portrait and equipment count. The original server controls the timer.
`verify_combined_expansions.py --include-native-world --include-advanced-protocol
--include-live-forms` requires the three races, matching server build, clean
native/client/server exits and restored QA fixture. This accepts the Bainshee
form cycle specifically, not every expansion ability or normal deployment.
The private observer binary is separate from `SharLobbyHost`; existing creation
UI evidence continues to pin its original binary.

`prepare_combined_expansion_data.py --workspace PRIVATE_WORKSPACE` exercises
both spell proposals, Vampiir career associations, six missing original starter
templates and five original Shar/Minotaur starting records together. It requires
the joint native acceptance, an offline marked QA database and pinned DOL
references. Independent startup proposals receive unique surrogate IDs in the
combined package; original coordinates remain unchanged. All SQL is rolled
back, then the offline fixture's exact original bytes are restored because
SQLite rollback alone can retain physical page/header differences. The output
is a JSON insertion proposal, not activation, inventory grants or a played DB.
The successful combined dry run adds 254 spells, 253 spell associations, four
abilities, 19 career associations, six item templates and five startup rows.

To test the complete package rather than individual class inserts, pass
`--combined-data PRIVATE_WORKSPACE/Reports/combined_expansions/data_integration/proposal.json`
to the combined creation or starting-spell harness. This writes separate
`_preloaded` evidence, applies only INSERT statements to a marked database under
`ProtocolQA`, and retains the harness's normal full-fixture restoration. The
package's source inputs are immutable build/proposal receipts, avoiding a
self-reference to the evolving joint acceptance summary. Every case records
the complete data-row payload hash.

`verify_combined_data_rollback.py` uses in-memory copies of an explicitly marked
QA backup to verify wrong-marker rejection, rollback after a late startup-ID
collision, and duplicate-package rejection. A separate tiny temporary database
also proves that a matching marker outside `ProtocolQA` cannot authorize writes.
The source backup stays unchanged. `--include-preloaded-data` on the joint sealer
requires those four checks, four Minotaur creations, ten Shar promotions, the
Bainshee and Shar Vampiir promotions, and a live native Bainshee cycle, all using
the same complete payload and combined server.

`prepare_review_expansion_delta.py` is read-only. It compares that accepted
package with the existing private review by semantic identities, preserves
matching rows, reports conflicts and reallocates only numeric association/startup
surrogate IDs. It produces a separate data delta; it never replaces the review
DB, writes progress records, enables races/classes or changes launcher binaries.

The review delta installer defaults to an in-memory dry run against the existing
review. It hashes every existing row in all 126 tables, excluding only the
explicit insertion identities, and verifies that they survive unchanged. With
`--apply`, it additionally reserves the private TCP/UDP ports, backs up the
review through SQLite (including committed WAL data), backs up server libraries,
installs the accepted joint server and inserts only the prepared missing data.
Failures restore old libraries and, if necessary, the saved logical database.
Successful installation never replaces the review database or activates another
race/class. The optional launcher receipt checks the installed library hashes.
The normal launcher, normal DB, WORK and existing review characters are separate.
After installation, the actual native menu smoke passed without world entry;
character, inventory, quest and task table hashes matched the pre-migration backup.

## Joint class behavior

The creation/promotion gate is followed by original class behavior with the
**complete preloaded joint data**, rather than independently inserted spell
subsets. `run_combined_vampiir_behavior.py --workspace <bridge> --install <game>
--mode power|buff|bolt` uses the existing marked disposable fixture and accepted
joint server. The power case starts empty and requires real melee damage to
generate power. The buff case trains with original point costs, checks resource
consumption/effect state and saved learned spells. The bolt case rejects a target
marked unseen, supplies the actual native geometry probe result, and requires
the original instant ability to gain power without inventing health damage.

`run_combined_bainshee_behavior.py` uses the same arguments with modes `training`,
`combat`, `ward` and `barrier`. Training must survive saved reentry. Combat uses
normal player privileges, requires movement to interrupt, actual health damage,
mana consumption and native answers to server sight queries. Protection probes
require the original released client-effect identities, not fabricated packets.
Run each case sequentially; all use the same private fixture ports and restore
their database, configuration and candidate libraries before the next case.

`verify_combined_vampiir_behavior.py` seals the three Vampiir reports.
`verify_combined_class_behavior.py` additionally seals the four Bainshee reports.
Both pin the full data payload and joint binary receipt and require a complete
server/UI spell list, successful normal shutdown and restored private fixture.
Output is separate from earlier creation/form receipts so new behavior witnesses
do not retroactively relabel those narrower checks. Spell aesthetics, audio,
complete class coverage and normal deployment remain separate acceptance.

The joint sealer accepts `--include-class-behavior --include-private-review`
in addition to its earlier gates. It requires all seven behavior witnesses,
checks the actual six installed private-review libraries against their receipt,
and includes the prior live-menu/progress-preservation evidence. Its pending
status then advances to owner review and normal delivery: the completed private
review migration must no longer appear as work still waiting to be installed.
