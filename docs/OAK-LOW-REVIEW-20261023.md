# Oak and dense LOW shrub — local LAB review

The owner requested a new impressive broad oak with a thick trunk and prominent
roots, and explicitly clarified that LOW TREE should be a dense shrub with
foliage reaching almost to the ground. The approved elms and birches are retained.

References supplied in the chat guide the oak silhouette, roots, bark and lobed
leaves. The two AVIF shrub references and the listed photos were no longer on
disk when checked; visible attached photos remain the visual reference. A photo
labelled Betula pendula Crispa is not used as an oak leaf template; the rounded
lobes in especie_071_02.jpg guide the oak leaf outline.

Original models: HOak Tree, model 7 (269 fixtures), 20.2895 metres above the local
origin; Low Tree, model 40 (52 fixtures), 12.5379 metres. The new oak retains its
height with a broad crown. LOW becomes a 6.5-metre dense multi-stem shrub with
low foliage, as requested, rather than retaining the original narrow tree form.

Deterministic rooted branch hierarchies constrain child radii to at most 67% of
the parent at their attachment. Roots, trunk and load-bearing boughs are welded
through a smooth implicit union, checked closed with no non-manifold edges.
Fine twigs and petioles attach to actual parent branches. Leaves are individual
geometry, without alpha cutout cards or inter-leaf connection networks. The oak
has lobed leaves, LOW has small oval leaves. Anisotropic crown scaling transforms
normals with the inverse transpose. No global deployment or distance optimisation
is included in this two-specimen near-detail review.

Native scenes use a matte triplanar bark material: roughness 0.98, zero metallic,
specular and emission. The oak bark albedo was generated with built-in imagegen;
the exact prompt and unmodified bitmap are retained with the local material.
The packed scenes embed their shaders and texture. Source GLBs also embed the
image and disable specular through KHR_materials_specular.

Isolated real-zone A/B renders check roots, normals, materials, fixture-transform
restoration and unchanged collision count at 14:00. The two labelled specimens
are placed at the existing review positions with Inspector GO TO entries. The
Inspector GLB metadata reader is exercised against both actual sources before
delivery. Automated checks are distinct from owner visual acceptance, which is
pending for these two specimens.

The previously approved birch review configuration is saved as
`.enhanced-session/elm_trial/review_stand_approved_birches_20261023.json`.
The shared 661-elm activation remains byte-identical. Stock assets, physics,
server and player data are unchanged. No game or server is restarted.

All code, models, materials and references stay local per the owner's instruction.
Recovery assets and an inventory are retained privately in the local Remasters
checkout under `graphics/zone207/oak-low-review-20261023`.
