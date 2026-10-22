# Connacht water capability trial — 2026-10-21

Owner authorized material improvements plus small real geometric waves in the existing isolated LAB. Original playable installation and server data are unchanged. This is an experiment before final art and optimization, like the accepted grass, elm, path, stone and ivy trials. Stone texture and realistic ivy leaf detailing remain deferred at the owner's request.

Implementation lives under `enhanced/terrain/`: `export_water_trial.gd`, `build_water_trial.py`, `prepare_water_trial.gd`, `water_trial.gdshader`, `water_trial.gd`, `preview_water_trial.gd`. Only the LAB entrypoint attaches the optional controller; stock `game/water.gdshader` and `game/zone_loader.gd` are intact.

Scope: zone 207's Water_River, nominal height 117.25 m. No ToA, other realms or other zone changes. Geometry comes from the native builder's exact 10,077 quads, including its flood-connected border. Python bakes shared vertices, ground-depth vertex data and two mesh densities offline; the main thread only loads resources. 161 chunks of 51.2 m, near spacing 0.8 m, original coarse spacing 6.4/3.2 m. Dense meshes are only drawn within 140 m of their bounds center. Actual geometric displacement fades at 45–85 m, safely before the transition, so both LODs coincide at their boundary. Additional normals stay visible further away. Near global triangles 973,824; far 20,154. 322 compressed mesh resources total about 4 MB.

The lit transparent shader uses actual scene lighting, original shared bump and cloud textures, analytic wave slopes, angle-dependent Fresnel sky colour and depth absorption/shore fading. Depth reconstruction follows Godot's reversed-Z and supports Vulkan/OpenGL NDC conventions. Three geometric sine waves have 4 cm maximum combined amplitude; lengths 4.8/2.8/1.9 m fit the near grid. Vertex depth attenuates movement at banks. Swimming level and collisions remain stock. Sky reflection is a fallback based on the existing cloud map, not planar/SSR object reflections; these were explicitly deferred.

Controller modes: 0 original, 1 new material on coarse copies, 2 material plus nearby displaced mesh. **Ctrl+Alt+U** cycles (Alt+F9 conflicted with the owner's video recording). Existing source water remains attached for its normal light/texture updates, hidden only while the trial is enabled. No original materials, meshes or physics are mutated. A shared new material copies sun/sky and bump/environment parameters from the original. Scene removal restores original visibility; reload reapplies mode. Guards validate original zone, source shader, loader, heights, mask, bump/cloud textures, original vertex fingerprint and generated mesh hashes.

Actual Vulkan render validation passed modes/views/day/night, original mesh/material/transform/visibility restoration, unchanged physics and water-level queries, unload/reload and rejection of a bad asset hash. LAB entrypoint compilation passed. A separate automated LAB login was refused because the owner's current LAB session was already open; no attempt was made to stop that session. Thus live character verification of this water change remains for the next LAB launch. Do not describe the offline preview as manual gameplay.

Uncapped 1440×960, GTX 1080 Ti, 60 frames/mode/view, no NPCs in preview, concurrent owner LAB: median frame-time increase 0.3–2.2 ms, worst at the water line with high screen coverage. This is indicative, not a combat benchmark or isolated GPU measurement. The workspace output `outputs/Prueba_agua_Ardee_20261021` holds exact measurements, screenshots, comparison launcher, backups and guarded activation/rollback. `.enhanced-session/water_trial/active.json` currently enables the next LAB launch.

References used: [Godot depth reconstruction](https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html), [spatial shaders](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html), [visibility ranges](https://docs.godotengine.org/en/stable/classes/class_geometryinstance3d.html). No downloaded scripts or new AI-generated raster assets are used.

## Surface grid follow-up, 13:21 screenshot

Current shortcut: **Ctrl+Alt+U**, verified through all three states; Alt+F9 no longer toggles water. Owner clarified and marked large tile-like patches throughout the surface. The earlier conclusion about fine bump detail being the main cause was incomplete; do not report that as a proven diagnosis.

A guarded smooth_v2 variant is now active. Dense spacing is 0.4 m rather than 0.8 m (3,895,296 globally prepared near triangles; only nearby chunks draw); far meshes and the safe flat transition remain unchanged. Resources are in a new subfolder, preserving the already loaded v1 resources. New pixel-filtered, continuously warped analytic ripples also replace the old bump sampling in the trial shader. Original source assets, water height, 4 cm amplitude and collision are unchanged. Active/latest pointers and control script preserve guarded restoration to the original pre-trial state.

Full real-render mode/restoration/physics/level/reload/hash-rejection checks passed at the new density. Current benchmark medians: original 5.0–5.3 ms, new 5.5–8.3 ms across the views, with the concurrent owner LAB. Approximate half-millisecond additional geometry cost compared to the previous version. Reports and screenshots are under Ajuste_cuadricula_132147/Malla_suave. Runtime water shortcut check passed separately. Root-cause elimination of every large patch in the annotated camera is not yet confirmed; ask the owner to inspect after restarting, rather than claim it is completely fixed.


## 13:54 / 13:57 user regression — authoritative current state

Owner reported smooth_v2 was worse: large patches persisted and the procedural crossed micro sines produced a dense tiny grid. The claim that increasing tessellation would solve it was unsupported. Retired smooth_v2 from active/latest, leaving its resources archived. Reverted to original 0.8 m private mesh resources. Removed analytic fine-ripple lattice, restored original irregular bump detail with reduced amplitudes and positive mip bias. Retained approved river colour, transparency, Fresnel and lighting. Real wave field now has a single prevailing direction with curved irregular phases and analytically matched gradients; no perpendicular macro-wave lattice. Maximum amplitude remains 4 cm, safely faded near shore and distant LOD transition.

New actual-render validation and images: Ajuste_135448/Comparacion, original 0.8 m meshes. Restoration, water level, physics, reload and bad-hash rejection pass. Tiny lattice absent in reviewed captures; definitive resolution of the user's large patches remains for their camera after restart. Ctrl+Alt+U remains verified. Root manifest is current again, with the updated shader; smooth_v2 is no longer the active candidate.


## 14:12 spacing follow-up — current accepted baseline

Owner confirms the grid texture is solved. Authorized fewer, broader, less repetitive crests and weaker distant stripes. Shader now uses wavelengths 9/6.5/4.8 m, smooth per-component amplitude envelopes that interrupt long crests, with analytic envelope derivatives. Macro normal contrast fades at 25–130 m, fine texture detail at 45–180 m, preserving near detail. Geometric shoreline/distance fading, 4 cm upper bound, approved colour/alpha/reflections and original 0.8 m mesh remain unchanged. Five-view actual-render checks passed; report/captures in Ajuste_141225/Comparacion. Existing owner session was not restarted. Ctrl+Alt+U unchanged.


## Owner acceptance after 14:12 spacing adjustment

Owner confirms the water now looks natural and approves the capability trial. Grid is resolved by their in-game review. Water is still somewhat opaque; transparency/opacity is explicitly deferred to the final corrections phase alongside tree, plant and other art fixes. Do not continue polishing water now. Keep the current shader and Ctrl+Alt+U comparison available.
