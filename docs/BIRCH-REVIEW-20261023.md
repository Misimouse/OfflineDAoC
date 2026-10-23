# New single and three-stem birches, 2026-10-23

The owner approved the final ELM/ELM2 pair, then requested new birches built from
scratch using supplied photographs. Two forms are required: one tree and a group
of three distinct trees. The new material must be matte in daylight.

Stock models in Connacht are `hbirchsingle.gltf` (61 fixtures, 132 triangles) and
`nbirchtree.gltf` (288 fixtures, 210 triangles), with above-ground tops of 24.2473
and 23.3670 metres. They use the source `ambient_only` material path. Stock meshes,
materials, fixture transforms and physics remain unchanged by this LAB review.

The new deterministic geometry starts with a rooted hierarchy. Child bases are
embedded at their sampled parent centreline, with radii no larger than 44% of the
parent radius. Tube frames use parallel transport to avoid twists. Primary limbs
rise, while fine outer shoots droop. Each individual serrated leaf has a petiole
connected directly to an existing shoot, not to a neighbouring leaf. There are
no foliage cards, alpha cutouts or disconnected inter-leaf networks.

The single specimen uses a denser hierarchy. The grouped specimen has three
independently generated stems with separate root positions, lean, crown and bark
phase. Each root samples terrain height separately when placed, embedding 4.5 cm.
The original model heights are retained. Vertex normals and triangle winding are
checked, and the source GLBs embed their bark image and zero-specular material
extension. Wood radius metadata is in UV2, leaving normal vertex colours valid
for generic GLB viewers and Forge exports.

Materials are fully lit, roughness 0.98, specular 0, metallic 0 and non-emissive.
The birch bark albedo was generated with the built-in image generation tool; exact
prompt and provenance are stored with the private material. Leaf geometry, green
colour variation and veins are native mesh/shader data. References guide shape,
leaf outline and bark; they are not projected as whole trees onto planes.

`prepare_birch.gd` packs self-contained native scenes. `birch_root_seating.gd`
positions the three roots independently without creating or changing collision.
`preview_birch.gd` compares against each original fixture at 14:00, captures the
bare skeleton and near views, and checks roots, normals, material settings,
original-slot restoration and unchanged collision count. Obstructing tree visuals
are hidden only in that isolated render and restored afterwards.

The LAB review stand reuses the two existing review positions and Inspector GO TO
identities for the new birches, with native source GLB paths exposed for resources.
The accepted elm pair is preserved in
`.enhanced-session/elm_trial/review_stand_approved_elms_20261023.json`. Existing
661-tree activation stays byte-identical. No running game/server is restarted.

These near-detail specimens are for owner review; forest-wide replacement and
distance optimisation are separate from this two-specimen preview. Source code,
references, GLBs, native scenes, generated albedo, prompt and checks are archived
privately under `graphics/zone207/birch-review-20261023` in Remasters.
