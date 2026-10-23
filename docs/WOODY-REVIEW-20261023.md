# Connacht woody props and final tree review — 2026-10-23

The owner approved the previous new silhouettes and realistic leaf finish, except
DEATH, for which the same shape with denser trunks and branches was requested.
The owner also requested new STUMP/LOG shapes and textures, and asked to retain
natural textured moss or ivy if present on the old models. Keep everything local;
the owner's no-GitHub-upload instruction remains in force. Water stays approved
and unchanged.

## Original-resource investigation

Stock `models/hstumpy.gltf` and `models/hlog.gltf` both reference the same original
`h_stmp.png`: a 256px atlas containing bark, cut wood and a green leafy/moss-like
patch. Neither model has a separate ivy mesh or ivy material. Species cannot be
established from this old patch alone; the new props interpret it as low woodland
moss, not large ivy leaves. Stock files remain untouched.

STUMP is now a continuous irregular trunk with seven unequal root buttresses,
a bark rim and separate exposed endgrain. LOG is a round tapered fallen shaft
with an attached uprooted root plate and two sawn branch stubs. The wood texture
is reused from the approved oak; new endgrain and moss bitmaps are generated
specifically for these props. Endgrain is mapped only to the cuts. Moss follows
patches on lower stump wood/roots and upward-facing log bark. Its matte material
includes a small physical surface offset and mipmapped fine moss detail; it is
not a glossy green coating or foliage draped over the cuts.

Both props retain the original fixture placement conventions. LOG's axis height
follows its taper so that the underside rests at the ground reference, rather
than leaving its narrow end suspended. Root collars use the existing terrain
seating helper. Arbitrary population placement across steeper slopes remains a
separate rollout concern; the original collision geometry is unchanged.

## DEATH and remaining foliage

DEATH starts with the previous deterministic winter scaffold. Additional leaders
are generated after that scaffold's random sequence, preserving its existing
branch paths, with five additional main leaders and extra mid/fine laterals.
Branches increase from 783 to 2,403; triangles increase from 100,576 to 203,730.
Child radii stay at most 0.65 of the parent radius, taper stays monotonic, and all
branch origins lie on their parent. Its welded major surface is closed, with
zero non-manifold edges. This is density refinement, not an unrelated silhouette.

Both elms already had the detailed leaf materials from the previous pass; those
approved native scenes are retained unchanged. Both birches, OAK and LOW likewise
retain their newly approved leaf finish. GROVE now adds restrained lengthwise
surface detail and stomatal variation on the existing opaque needle geometry.
Its geometry, bark and stable canopy shadows stay unchanged. The updated needle
shader is packed in the native scene; the retained source GLB is geometry provenance.

## Coverage and validation

The actual zone 207 catalog contains nine tree types: Dead Tree, Grove Tree,
Birch Tree (three trunks), HOak Tree, Elm, Elm2, Birch Tree Single, Low Tree and
Bare Tree. All nine now have review specimens. STUMP (five fixtures) and LOG
(three fixtures) are the two additional woody props. No other tree type is left
unaccounted for in this catalog. This statement concerns model coverage, not
replacement of every stock instance throughout the zone.

Current LAB review stand has eleven specimens. OAK/LOW, elms, birches and BARE
keep their previous scenes and positions. GROVE/DEATH are updated in place;
STUMP/LOG are added alongside them. The backup before this pass is
`.enhanced-session/elm_trial/review_stand_approved_forest_before_woody_20261023.json`.
New bundles are `.enhanced-session/forest_trial/bundles/woody_*_20261023/`.

Automated checks cover finite positions, unit normals, outward winding, real
fixture preview placement, terrain seating, matte materials, visual restoration,
unchanged collision counts and Inspector GLB parsing. Renders run in isolated
Godot processes; no server, user client or player position is restarted/changed.
Live owner validation of the new props and DEATH refinement is still pending.
The eleven-specimen restoration/AA test passes with frame boundaries between
viewport changes. An initial abrupt-toggle harness run exited before completion
without a diagnostic; this is retained in the local output logs, not presented
as a passing run.

The shared 661-elm activation remains SHA-256
`8197498e23c4213df9dd8d37c7c89c9b9e2f96eb7715e83e74f9c7651255ef99`.
Water manifest remains SHA-256
`ba0e22e5b6da59fb6fd923ad82fd68b528b66b3217a2440bd1f2d50abf6a00a5`.

Private local recovery archive: `graphics/zone207/woody-review-20261023` in
Remasters. Exact built-in image generation prompts and the unmodified generated
PNGs are stored under `payload/review/materiales/`. Native scenes embed their
materials and textures; inventory SHA-256 entries record recovery project paths.
Prior immutable forest and oak-low archives supply the previous accepted scenes
and generator dependencies. No played databases, credentials or game logs belong
in this archive. No uploads or pushes are authorized.
