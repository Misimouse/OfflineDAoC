# Catacombs content audit

This is a read-only inventory, not an expansion activation or a world replacement.
Run `audit_catacombs_content.py --workspace <bridge> --install <playable>` after fetching
the pinned public tables with `fetch_catacombs_world_reference.py`.

## Verified reference

Dawn-of-Light/db-public revision `b5b29c2ada7695414b94f5fa110eb505a477d007`.
Every public payload is checked against its original Git blob. Large world tables
are cached compressed; fetched text is accepted only if its original blob can be
recovered despite transport newline normalization.

The installed database is copied with its WAL into a disposable private directory.
Only the copy is opened, query-only, and removed after inspection. Account/player
rows are neither exported nor included in the report. The installed world is not
opened for writing or checkpointed.

## Findings, 2026-11-05

| Content | Installed | Pinned public DOL |
| --- | ---: | ---: |
| Catacombs regions declared (DB Expansion=3) | 230 | 230 |
| Catacombs regions with population | 4 | 40 |
| Catacombs mob/NPC spawn records | 83 | 20,860 |
| ItemTemplate, all expansions | 37,342 | 32,278 |
| NPCEquipment rows, all expansions | 55,614 | 51,296 |
| DataQuest definitions, all expansions | 1,540 | 8 |
| InstanceXElement entries | 0 | 120 |

20,777 public Catacombs spawn IDs are absent locally. This does not authorize
bulk insertion: spatial definitions, script classes, brains, factions, paths,
loot/merchant lists, template replacement rules and visual assets remain gates.

The Catacombs population references 994 non-sentinel NPC template IDs. Thirty
are absent locally; 29 are absent even in the public NPC template file. The
`-1` sentinel is excluded. The 3,042 referenced equipment template IDs are all
present locally. Template equipment alternatives are split by semicolon as in
GameNPC.HandleInventory; inline `slot:model` definitions are tracked separately.

503 direct mob Model IDs occur in those public Catacombs regions. Godot's monster
catalogue contains 436 directly; the normal native catalogue contains 23 directly.
These are catalogue membership counts, not render acceptance: human aliases,
template model overrides, actual files, skins, equipment and animations must be
resolved before calling an appearance supported or absent. No Catacombs zone in
Godot's zone index is marked built (229 indexed entries). Original-client files
may still contain their assets; indexing does not prove an exported playable map.

The public ItemTemplate has 2,265 IDs absent locally across **all expansions**.
Do not label every one a Catacombs item: that table has no reliable expansion tag.
Armor uses body sections/skins/extensions; its Model IDs are not standalone weapon
or monster meshes. Fewer public items than installed also does not establish a
superset in either direction.

The installed base contains expansion definitions and equipment already. The
claim that it is exactly version 1.65 is unconfirmed. Expansion=3 is established
through Region.Expansion = DB Expansion + 1 and eClientExpansion.Catacombs=4;
this is a content marker, not a certificate of a historical client ruleset.

## Import boundaries

1. Keep the current world and saves. Produce additive, conflict-reporting candidates.
2. Resolve the missing NPC template references and script/data dependencies first.
3. Validate a small Hibernian population sample in an isolated fixture, including
   resolved template models, equipment, animations, interaction and saved re-entry.
4. Dungeon/instance validation is a separate block: 120 InstanceXElement entries
   are not 120 complete working instances, and require generator/runtime support.
5. Keep existing quest definitions. Public Quest.json contains character progress,
   not quest definitions; it is excluded. Future quest interface modernization
   remains queued and does not belong in this audit.
6. No normal launcher, WORK map, expansion switch or player progress changes here.

Evidence: `<bridge>/Reports/catacombs_content_audit/comparison.json` contains
per-region counts, missing IDs, verified source revision and snapshot hashes.
