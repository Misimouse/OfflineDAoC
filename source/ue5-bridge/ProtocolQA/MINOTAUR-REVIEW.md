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

For the live native witness, add `--native-world-probe` to the combined
Minotaur original-start matrix. This focuses on one Warden-path creation and
reentry; the full four-career matrix remains independently sealed. The harness
then enters that disposable character and closes its protocol observer socket.
The disposable transport first explicitly releases its observer peer; this
test-only command is injected into the QA copy, never the production gateway.
Unreal then takes the bridge's single peer, renders the actual Connacht map,
records connected/navigation evidence and a screenshot, and logs out normally.
Only then may the harness restore its disposable fixture. Reports go to a
separate `minotaur_original_start_world` directory.

`verify_combined_expansions.py --include-native-world` additionally verifies
this witness, the unchanged original bind, normal shutdown and absence of
missing local weapon models/bones. It does not mark Bainshee/Vampiir native
world entry or the Horn Size feature as accepted.

The swatch export reuses the original Godot menu's sampling functions in a
private adapter. Adding color picker controls does not modify rendered materials,
textures or morph geometry. Shar and Vampiir native regression cases run against
the same private plugin library.
