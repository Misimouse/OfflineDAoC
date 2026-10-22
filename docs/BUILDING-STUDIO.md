# Building studio — local prototype, 2026-10-21

Standalone Godot scene-tree application: `source/new-client/godot/enhanced/building_studio/main.gd`. Uses the installed Godot 4.7.2 Mono runtime and the existing converted zone207 assets. No new external dependency or service. Does not connect to a server or change live replacements.

User entry point: `C:/Users/imatc/Documents/Codex/2026-10-19/referenced-chatgpt-conversation-this-is-an/outputs/Taller_edificios_20261021/Abrir taller.lnk`. Same folder includes launcher, Spanish instructions and verification artifacts.

## Supported workflow

Three verified presets: helfshack, hlurikhut, hshop. Custom converted NIF glTF can be selected; requires extras.nif_materials and the zone models/textures directory structure. Original layered materials are reconstructed by NifMaterials. Collision/climb meshes are omitted; door panels are posed closed from nif_doors. Export is a static graphics copy, without gameplay door animation or updated collisions.

Whole-model orbit/zoom; click a piece or choose a base texture group; classify material; replace colour image; mark normalized UV regions; load a grayscale height image or use source luminance as a draft; generate actual subdivided displaced geometry; compare exact original; clay view; restore selected material; export and reopen recipe.

Classification suggestions use explicit name rules, not AI recognition. Catalog keys combine base texture name with SHA256 of source image bytes. Classification and normalized regions can be reused where that texture has the same interpretation. Grouping is by base texture, so existing layered variants are retained on individual pieces.

Relief generator welds compatible position/normal/UV vertices, adaptively subdivides conforming triangles, pins UV/topological seams, fades deformation over two boundary adjacency steps, and recomputes normals. Carries UV2 and vertex colours. Base UV channels other than UV0 and custom vertex channels are rejected. Up to 60,000 vertices per surface and 180,000 triangles per selected material operation; a failure discards the whole pending material operation. This is a local prototype cap, not a measured game performance guarantee. Different material operations can accumulate; inspect the displayed whole-building triangle count before choosing results.

Depth is positive outward displacement capped by the UI at 6 cm. Luminance is not inferred structural depth. This does not create architectural window holes, bevel every silhouette edge, reconstruct interiors or automatically turn painted features into modeled parts. Stone, wood and roof are eligible. Mixed materials require regions; all unmarked areas are protected when regions exist. Later rectangles override earlier ones. Window/door/glass categories are protected from generation.

## Data and reversal

All user state goes to `.enhanced-session/building_studio/`: catalog.json (temporary file then rename), copied images by content hash, timestamped export folders. Each export has bundled `edificio.scn` and `receta.json` with source hash, catalog, per-piece generation report and applied rule snapshot. Reopening recipes uses applied geometry rules, not ungenerated pending UI choices. Existing colour changes are retained. Native scene chosen to retain the layered shaders and embedded textures; no GLB export claimed.

Model generation only changes new ArrayMeshes. Original imported meshes and input files are preserved. Source glTF SHA256 is rechecked before export. Selected restore clears the applied mesh, colour replacement and height mode while retaining category/regions. Close and rename private building_studio state folder to reset the entire studio. No client/master rollback needed because these are not modified.

## Validation

`--script res://enhanced/building_studio/check_geometry.gd` runs synthetic geometry assertions: real movement, source vertex immutability, protected window UV region, pinned borders, outward normals, UV2/colours retained, unsupported input rejection.

`--script res://enhanced/building_studio/main.gd -- --self-test=ABS_OUTPUT_DIRECTORY` runs actual Vulkan UI/application checks in isolated state: all three buildings load; actual displacement and triangle growth; source hash unchanged; exact original comparison; catalog reload; private colour replacement; bundled export reload with matching vertex count; category protection; saved generation recovery; recipe opening; picking a rendered piece. Saves checks.json and taller.png. Test mode does not load the user's catalog. Exit 1 if any boolean check fails.

No performance claim for the live game or validation of automatic gameplay integration. No server was started, no user session was closed, no original client assets were overwritten.
