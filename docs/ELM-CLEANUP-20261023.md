# Elm cleanup after close-camera owner review, 2026-10-23

The owner rejected the previous leaf-to-leaf twig network: its straight routes,
crossings and attachments looked like wires and worsened Elm2. Automated rooted
connectivity did not establish botanical plausibility. The old review remains
archived for history; this version completely removes its additional wood mesh.

Both candidates retain the two original mesh parts. Elm2's wood
vertices, UVs and triangle indices are byte-identical to the previously accepted
pruned model. The first elm retains the reinforced fused wood from the preceding
review. There are no leaf-to-leaf links. A third part contains only short curved
shoots rooted directly in existing wood, not the rejected inter-cluster network.

Existing foliage clusters close to wood keep their positions; more distant ones
move closer. Tapered curved shoots attach them directly to existing wood. Routes
are bounded to 0.347 source metres (under 0.7 metres at either fixture scale).
Parents are at least 0.012 source metres in radius; each new shoot base is at
most 72% of its parent radius. No shoot is rooted in another foliage cluster.
The most isolated clusters are removed rather than bridged across empty space.
First elm retains 3,667 of 4,211 clusters (12.9% removed); Elm2 retains 5,068 of
5,320 (4.7% removed). Embedded foliage images and
UVs are unchanged. This is cluster-level cleanup, not reconstruction of each
individual leaf's petiole inside the supplied atlas.

The first elm's bark shader keeps the supplied colour, normal and roughness maps
and blends differently offset samples to reduce repeated bright vertical bands.
Both side projections follow source Z-up grain. Source image pixels are unchanged.
It retains double-sided rendering, matching the supplied material, with restrained
normal strength and specular response. Foliage materials, shadow settings and
review-stand temporal AA remain unchanged.

`preview_elm_candidate.gd --leaf-review --repair-review` includes close views inside
and near the outer crown, alongside roots, bark and the whole tree. These are
needed because the previous distant views concealed poor small-branch routes.
Automated checks separately verify source geometry/UV/image preservation, absence
of the rejected wire mesh, root contact, stand destinations, collision preservation and
temporal-AA restoration. The owner still judges the appearance and reduced crown
density in the actual game.

Private scenes are in `clean_first_20261023` and `clean_elm2_20261023` under
`.enhanced-session/elm_trial/bundles`. The same two LAB positions and Inspector
identities are retained. `review_stand_before_cleanup_20261023.json` restores the
preceding pair. Shared activation of the 661 trees stays byte-identical; no server,
database, stock art or running game is modified. Private art and the reproducible
cleanup pipeline are archived in Remasters under `elm-cleanup-20261023`.
