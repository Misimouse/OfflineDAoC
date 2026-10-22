# Ardee stone and ivy trial — 2026-10-21

Bounded private graphics experiment requested by the owner. No stock content or database writes. The owner is exploring engine capabilities; final art, broader distribution and global optimization are deferred.

- Zone 207, Connacht. Four stone fixtures: 1429, 1431, 1430, 935 (three original models, the last reuses Stone 1). Four architectural fixtures: 334, 335, 336, 1107.
- Start from original stone meshes, weld the closed manifold, partially smooth subdivision while preserving the original envelope/buried base, then bake a shallow fracture and worn hollows. 15,360 triangles per stone, compared to 60 originally. Original placement and original physics retained.
- New triplanar material: Poly Haven Rock 3 by Rob Tuytel, CC0, colour/OpenGL normal/roughness at 2K. Maps and generated texture resources are shared, not embedded per stone scene.
- Separate ivy dark layers (`hclimbvine`, `hbasevine`, UV2) guide prebuilt solid leaves and stem tubes. White opaque regions in hbasevine are excluded using a green mask. Old independent layers are disabled on private material copies. Ivy already baked into complete building base textures remains in scope for a future pass.
- New art is generated offline. No geometry generation while moving through the map. Stone render distance follows original instances; ivy detail fades at up to 70 metres times the view setting.
- Runtime is `enhanced/terrain/stone_ivy_trial.gd`, attached by the isolated `enhanced/lab_session.gd` after the existing tree and path controllers. Alt+F7 toggles stone, Alt+F8 ivy. Original and new choices are independent.
- Private resources and manifest: `.enhanced-session/stone_ivy`. Guard zone/model/texture/scene hashes and expected exact fixture IDs before changes. Validate all original model-part transforms before changing any instance. Only original instance transforms are temporarily hidden; clones have private materials. Zone unloading restores originals and subsequent zone loading reapplies the chosen options.

Pipeline: `build_stone_ivy.py` (numpy/Pillow) → `prepare_stone_ivy.gd` → `preview_stone_ivy.gd`. The preview uses the actual renderer and zone, with frozen lighting and eight camera views. No server or account is needed for it.

Automated render validation passed all four combinations, exact original transform restoration, collision identity/transform preservation, view-distance updates, zone unload/reload and rejection of an intentionally wrong scene hash without stock mutation. Separate real LAB login/shutdown passed with the existing elm, grass and path trials enabled. Both processes exited 0; existing render-resource shutdown warnings match the previous LAB session's RID counts. This was automatic login/shutdown, not manual gameplay or a combat performance benchmark.

The owner's workspace has the review launcher, before/after captures, reports, source backups, hashes and a guarded activation/rollback in `outputs/Piedras_hiedra_Ardee_20261021`. `Restaurar_originales.cmd` restores this art pointer for subsequent LAB launches and refuses to overwrite a later change. The lab entrypoint's original byte backup is included separately. No other realm or ToA is affected.
