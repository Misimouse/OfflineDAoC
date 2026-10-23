# Connacht replanting activated in LAB — 2026-10-23

Owner authorization: "Todos quedan aprobados, ya puedes replantar con estos
arboles la zona", with two refinements: realistic textured rock ivy and a credible
LOG root base with non-square moss patches. All storage remains local; no GitHub
uploads, game/server restarts, database changes or stock-source edits are authorized.
The approved water remains unchanged.

## Result and scope

The existing Connacht LAB fixtures now display the approved art by model type:

| Model | Existing fixtures |
|---|---:|
| Dead Tree | 18 |
| Grove Tree | 41 |
| Birch Tree, three trunks | 288 |
| HOak Tree | 269 |
| Elm | 326 |
| Elm2 | 335 |
| Birch Tree Single | 61 |
| Low Tree | 52 |
| Bare Tree | 6 |
| Stump | 5 |
| Log | 3 |

Total: **1,396 trees and eight woody props, 1,404 placements**. No other tree
type occurs in this zone catalog. Fixture IDs, yaw, scale variations and holder
positions are retained. The accepted review stand's art scale is retained per
type (1.32 for elms, 1.0 for the other types). Root seating samples terrain for
individual birch stems and rooted broad/conifer models. Stock physics stays as
before; decorative meshes add no collision shapes.

The full forest replaces the previous shared 661-elm trial and eleven labelled
review specimens at LAB startup. Their configuration files remain intact as a
fallback. The new controller hides original visuals reversibly, supports Ctrl+F9
comparison, mirrors view distance and restores original transforms and viewport
AA settings on unload. No artificial review duplicates or cleared review circles
are added when population activation is valid.

## Requested corrections

LOG keeps its approved shaft, cuts and endgrain. Its collar now has eight
asymmetric curved main roots, 24 smaller lateral roots and an uneven compressed
root face. Torn wood/earth coloration is assigned to the actual welded surface,
with no separate cover disc or hollow seam. Moss uses a continuous warped field
with curved, blended boundaries instead of the earlier grid-derived patch mask.
The approved STUMP material is unchanged.

The existing separate 3D ivy on four menhirs and four Ardee structures now samples
a new matte, mipmapped leaf albedo with palmate veins and tissue detail. All 12
leaf mesh parts keep their vertices, indices, UVs and placement. Stone bodies,
existing stems and their materials are preserved. This updates the existing ivy
overlay; it does not convert additional stock rocks or buildings.

## Detail and performance

Native mesh LODs reduce wood/shadow detail at distance. Opaque foliage uses
explicit whole-leaf/needle sampling levels (2, 8, 32 and 128 stride), with coverage
compensation. Close mesh indices and all original base positions are verified
unchanged. Extra distant vertices belong only to LOD indices. Group sizes are
validated against the actual leaf topology (26 oak, 12 LOW, 21 birch, 4 needle).
Elms retain their original atlas and use generated LODs on their native meshes.

The population controller adapts per-object LOD bias every 0.2 seconds. Detail is
highest within 22m, with progressively coarser tiers beyond 65/150/300m. Dry tree
branch silhouettes retain a higher minimum bias. Shadows-only canopy envelopes
stop beyond 300m, following view-distance scaling. New meshes/resources are shared
between instances rather than regenerated for every tree.

The final isolated renderer test on GTX 1080 Ti at 1440x900 measured new-forest
frame means of **23.34, 12.97 and 22.32 ms** in three fixed views (about 43–77 FPS),
versus **7.24, 6.95 and 6.97 ms** for stock visuals under the same AA profile.
The detailed forest therefore remains more expensive than the stock low-poly art.
Reported primitives include render passes, not just unique visible triangles.
These are isolated rendering measurements, not a guarantee for live gameplay
with players, NPCs or another resolution. The first default-bias full-zone test
rendered roughly 36–40 million primitives; final views render about 5.9–16.3 million.

## Validation

- All 1,404 fixture IDs unique and holder positions identical to source records.
- 1,319 root anchors checked against terrain seating, within 3mm of the target.
- Original MultiMesh transforms restored byte-for-byte after comparison/unload.
- Collision counts unchanged; region unload/reload and view-distance updates pass.
- Previous TAA and MSAA restored; AA changes are scoped to the active forest.
- LAB startup and Inspector bridge compile; active manifest/scene/stock hashes pass.
- All eleven model resources parse through Inspector without missing textures or
  UTF-8 errors. Inspector now links the replacement source for planted fixtures.
- Actual ivy leaf macro render shows veins and surface tissue. Full-zone and LOG
  placement screenshots were inspected. No running game/server was started/restarted.

Final passing run: `outputs/Replantado_20261023/population_release.log` in the task
workspace. Earlier harness failures are retained separately: an initial view-range
assertion omitted changing the static setting; an early class reference caused an
autoload compile-order warning. Both harness issues were corrected before the
final passing run and activation. The first foliage preparation also needed the
original tangent channel extended alongside distant vertices; final bundles pass
base-array equality checks and renderer tests.

## Activation, rollback and recovery

New pointers are `.enhanced-session/forest_population/active.json` and
`.enhanced-session/stone_ivy/active.json`. The latter points at the new
`stone_ivy/detail_20261023/manifest.json`, retaining the previous material resources.
Forest bundles are under `forest_population/bundles/*_20261023/`.

Before-pointer copies and a guarded activation record are stored in the task
workspace under `outputs/Replantado_20261023/before_activation` and `activation.json`.
Run that workspace's `work/activate_population.py --undo` with Python to restore
exact prior pointers. It refuses to overwrite any pointer changed after activation.
Removing the new forest activation causes LAB to use its previous elm/review path;
all new assets can remain stored without affecting that fallback.

The untouched previous elm pointer SHA-256 remains
`8197498e23c4213df9dd8d37c7c89c9b9e2f96eb7715e83e74f9c7651255ef99`.
The untouched water manifest remains
`ba0e22e5b6da59fb6fd923ad82fd68b528b66b3217a2440bd1f2d50abf6a00a5`.

Private local archive: `graphics/zone207/connacht-replant-20261023` in Remasters,
with a hash inventory and project recovery paths. Earlier immutable forest/woody
archives and the zone207 snapshot supply retained Inspector GLBs and original
stone textures/resources. New source LOG, all eleven population scenes, new ivy
scenes, pointer backups, checks, images and pipeline are archived in this pass.
No played databases, credentials or game logs are included. No pushes were made.

New ivy bitmap and exact prompt: `payload/review/materiales/ivy_leaf.png` and
`prompts.md`, generated using the built-in image generation tool. Existing moss
and endgrain images are retained from the approved woody archive.

Godot API references: [ImporterMesh LOD generation](https://docs.godotengine.org/en/stable/classes/class_importermesh.html),
[per-instance LOD bias](https://docs.godotengine.org/en/4.3/classes/class_geometryinstance3d.html).
