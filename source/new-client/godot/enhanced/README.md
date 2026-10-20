# Enhanced: Ardee grass laboratory

## Landscape extension

### Flower life and selective cleanup (v4)

`flower_insects.gd` adds three butterflies and two bees per patch. Actual transformed flower centres are the route anchors. Flights interpolate between nearby flowers (at most 2.6 m), with vertical bobbing, pauses, wing motion and culling beyond 20 m. Route sampling rejects clear masks and paths; isolated flowers get hovering rather than wandering. This is a client-only effect, with no server actors or sound. Routes and before/after positions are exported for validation. The Flores view follows a butterfly for inspection; Insectos toggles the effect.

`selective_clutter.gd` subclasses the original clutter builder and filters six explicitly named group 6 undergrowth items within 26 m of the active site. Seed grasses, tall grasses, other groups, tree fixtures and world data are preserved. It consumes the original tuft RNG sequence on a discard surface before skipping the geometry, so following vegetation does not move. A zero-area triangle prevents the original builder from committing an empty chunk. A/B restores/filters the original clutter in memory; rebuilding it can cause a visible pause in this prototype. This is not a global deletion rule.

The complete scene comparison includes the insects; their marginal frame cost has not been isolated. Dense vegetation still needs performance work. Existing engine rendering warnings are recorded with test results.

### Coverage and hillside trial (v3)

The current harness has two independently selected sites: the well parcel and a nearby green slope at zone-local metres (1190, 1180). Two low-cover mesh variants add 4–11 cm foliage before scale variation. A separate random stream keeps the existing well plants exactly where they were. Low cover aligns with the terrain normal and respects the same mask and physics exclusions.

The well keeps its local soil blend. The hillside has **zero terrain material overrides** and a greener foliage profile, with no dry tufts; its original ground is preserved. These are manually chosen site profiles, not automatic biome detection or verified regional transitions. Original ground clutter was retained in v3; v4 adds the selective cleanup described above.

Buttons Pozo/Ladera select the site, A/B toggles the treatment, and the camera remains consistent within each comparison. Capture now measures both sites at two distances, A/B/B/A, 45 warmup and 120 measured frames per segment. Higher coverage adds GPU cost and is not approved for world-wide deployment.

`landscape_trial.gd` / `landscape_patch.gd` extend the bounded experiment with nine plant families and 25 geometry variants (fine/broad grass, dry tufts, clover, basal rosettes, white/yellow flowers, narrow-leaf herbs and small ferns). All meshes are deterministic procedural geometry. Variant selection does not consume the placement random stream: plant count and positions stay identical to the previous landscape trial. Some existing plants are replaced by the new families.

Version 2 uses DAoC `h_soil` and `h_ground_scrub` textures at finer world scales through one terrain material clone on patch 6_6. It removes the large grass-photo base, mixes rotated soil samples to soften repetition, and brings ground and living foliage towards a shared muted olive palette. Petals preserve their colours; dry vegetation is dimmed separately. No resolution increase or AI processing is involved. The shader source is extended in memory; original terrain resources remain unchanged.

One 256x256 mask controls both local soil blending and plant coverage, with a soft irregular boundary, a cleared route from the well and a well exclusion. Its second channel gives continuous colour vigour variation. Physics queries reject placements whose first surface stands above the ground. The current placement mask is handcrafted for the parcel: original `grassmap`, `densemap` and terrain splat data were inspected, but are not yet the placement authority. Green/dry transitions across a whole zone remain unresolved.

Launch the extension with `--script res://enhanced/landscape_trial.gd`; the same `--4k`, `--capture`, `--out` and `--keep-open` arguments apply. Both plants and any local ground treatment toggle together. This is a graphics layout prototype with simple botanical meshes, not a finished photorealistic asset library or a full-game performance validation.

Standalone graphical prototype based on OfflineDAoC tag v0.37c. It loads actual zone207 terrain, fixtures and sky, retaining the stock ground clutter in both A/B variants. No server is started or contacted. No original scene, model, UV, shader or terrain file is changed.

`grass_patch.gd` builds a seeded patch of folded, tapered geometry blades as one MultiMesh. The prototype has varied heights/colours, anchored wind motion, an irregular feathered boundary, no cast shadows, and geometric distance reduction. It uses no raster texture or AI. Placement is deliberately limited to one experimental parcel near the Ardee well; this is not a production terrain mask, global vegetation system or replacement tree renderer.

`grass_trial.gd` is the SceneTree harness. Buttons switch original/geometry grass, three fixed views, orbit motion, wind and afternoon light. Launch with `--script res://enhanced/grass_trial.gd -- --out=<local-output-folder>`. Optional `--4k` requests a 3840x2160 viewport; `--capture` runs static A/B/B/A measurements and screenshots, and exits unless `--keep-open` is set. Window dimensions and actual screenshot resolution must be checked on the host. Rendering measurements include the existing scene and are not predictions of full-game FPS.

## Local preparation

- Use the matching v0.37c installed game and the bundled Godot .NET engine/runtime. The unchanged matching C# assembly can be copied for these GDScript-only graphics tests. This does not establish a C# build environment; C# development requires the SDK described in the upstream README.
- Exclude `source/new-client/godot/content/`, `.godot/` and `.enhanced-session/` from Git before copying. Never commit client content, copied binaries, accounts, databases, logs or user settings.
- `Prepare-Lab.ps1 -InstallRoot <existing-playable-folder>` copies only Ardee and selected shared dependencies into a separate project. It refuses to overwrite an existing content directory, uses independent files rather than writable links, and verifies copied content hashes. This helper is provided for reproduction; the first local preparation used equivalent copy operations, with all 560 Ardee files verified.
- Use a separate `APPDATA` folder and the matching bundled `DOTNET_ROOT`/`DOTNET_ROOT_X64` when running. Never pass server/account/password arguments to this harness.
- The partial content copy supports this laboratory, not the full login/character/game flow. Other zones and character assets are intentionally absent.

Closing the lab removes all runtime effects. The playable installation and Enhanced tools remain separate. The existing hstucwin2 Enhanced replacement, made before this laboratory, is present in the copied zone as well as the installed zone; it is held constant in both comparisons.

## Limits to evaluate

The ground under the patch is unchanged and can look different from the blades. Ground blending, road/building exclusions, streaming sectors, proper distance detail levels, grass shadows, interactive bending and full-game performance remain future tasks. Rendering warnings inherited from the current engine/project must be reported with results.
