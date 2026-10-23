# Forest materials and silhouettes — LAB review, 2026-10-23

Owner requested restrained realistic foliage detail, less oak shimmer, a conifer GROVE,
and two distinct dry trees. Owner subsequently authorized extending leaf detail to
the already accepted elms and both birches. Keep all work local: no GitHub upload.
Water was explicitly approved and is unchanged.

## Review stand

Nine labelled specimens are configured in zone 207 LAB. OAK and LOW keep their
previous positions and geometry; LOW remains a dense shrub with foliage to the ground.
The accepted ELM1, ELM2, single birch and three-trunk birch retain their geometry,
transforms and bark. Their new native scenes only replace foliage materials.
Elm atlas RGBA pixels, silhouette cutouts and alpha thresholds remain unchanged.
The source GLBs of these four retained specimens are provenance/Inspector geometry;
their updated foliage shader is embedded in `forest.scn`.

New GROVE is a tall conifer with attached needle shoots and plate-like bark.
DEATH has a broad winter crown with many tapered branches. BARE is a distinct,
asymmetric dry tree with gnarled leaders and a simpler open crown. Both stay leafless.
The new shapes use parent-limited branch radii, monotonic taper and welded main forks;
thin terminal sections are retained below the union's voxel resolution.

| New source | Triangles | Branches |
|---|---:|---:|
| GROVE | 1,172,640 | 3,967 |
| DEATH | 100,576 | 783 |
| BARE | 45,398 | 132 |

These are single review specimens, not a global population replacement. GROVE in
particular needs a population/LOD performance pass before any broad rollout.
Stock models and collision geometry were not overwritten.

## Foliage and movement checks

Opaque oak/LOW/birch leaf geometry now samples matte albedo detail with veins and
restrained surface variation. Elms receive subtle surface modulation over their
existing atlases. No metallic, emissive or glossy leaf surface was introduced.

Oak/LOW/GROVE use separate shadows-only cluster envelopes for stable canopy shadows;
wood retains normal shadows. In the review stand, TAA and MSAA 4x are scoped to the
review session and Ctrl+Shift+F7 compares the smoothing. Previous viewport settings
are restored when the stand is cleared. Global saved settings are unchanged.

An isolated fixed-sun oak probe tracks 37,984 world-space leaf sample pairs over
2.5 cm camera steps. Luminance jumps above 0.03 fell from 1,940 to 1,414 (27.1%);
mean delta fell from 0.00788449 to 0.00644497. This measures the combined candidate
shadow/smoothing profile, not texture detail alone, and does not establish zero
shimmer during live gameplay. Owner visual review of this pass remains pending.

## Validation and recovery

- New GLBs: finite positions, unit normals and outward winding pass.
- Retained four: per-surface vertices, normals, UVs and indices identical; bark unchanged.
- Native new-tree previews: real fixture placement, root seating, matte materials,
  original visual restoration and unchanged collision counts pass.
- Nine-specimen stand: reload/restoration, oak/LOW position preservation, unchanged
  collisions, restored TAA/MSAA pass. All nine resource rows parse in Inspector
  with no missing textures or UTF-8 failures. Adapter check is read-only.
- Renders use an isolated Godot process; no game/server restart or player movement.

Active stand: `.enhanced-session/elm_trial/review_stand.json`.
Before this pass: `review_stand_before_leaf_detail_20261023.json`.
Oak/LOW detailed-only checkpoint: `review_stand_oak_low_detail_20261023.json`.
New native bundles: `.enhanced-session/forest_trial/bundles/detailed_*_20261023/`.

The shared 661-elm activation remains SHA-256
`8197498e23c4213df9dd8d37c7c89c9b9e2f96eb7715e83e74f9c7651255ef99`.
Approved water manifest remains SHA-256
`ba0e22e5b6da59fb6fd923ad82fd68b528b66b3217a2440bd1f2d50abf6a00a5`.

Private local recovery archive: `graphics/zone207/forest-detail-review-20261023`
in the local Remasters checkout. Its inventory maps every archived payload file
to a SHA-256 and, for live files, its project recovery path. No credentials,
played database or game logs are included. Prior art archives remain immutable.

Generated bitmaps use the built-in image generation tool. Exact prompts and saved
PNG files are in `payload/review/materiales/prompts.md` and `prompt_olmos.md`;
the original user-named references are in `payload/review/referencias/`.
Generation helpers also depend on the prior local oak-low archive's original
source models and bark, as recorded by its inventory. Native bundles are directly
recoverable without regenerating images.
