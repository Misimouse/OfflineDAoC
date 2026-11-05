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
Creating additional characters is deliberately disabled in this copy until
their original starting areas are supported by the native map.

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
by the objects table's twelve Catacombs helmet columns. The three Minotaur
figures also have no full-helmet slot 9. Consequently this audit does not
establish playable helmet mappings. Numeric matches in unrelated texture,
effect or armour columns are different ID namespaces and must not be used as
helmet mappings. Do not force another race's full helmet onto the Minotaur.

The swatch export reuses the original Godot menu's sampling functions in a
private adapter. Adding color picker controls does not modify rendered materials,
textures or morph geometry. Shar and Vampiir native regression cases run against
the same private plugin library.
