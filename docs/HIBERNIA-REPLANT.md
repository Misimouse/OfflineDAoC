# Hibernia replant panel (v0.37c development branch)

A native Godot tool in `source/new-client/godot/enhanced/replant`. It prepares versioned vegetation masks using existing converted zone data. It never rewrites source assets or a database. ToA, Albion and Midgard are excluded by a region whitelist; Hibernia Classic (region 200) and Shrouded Isles (181) are the only allowed regions. Interiors and cities are not replanted.

## Local configuration and launch

Create `.enhanced-session/replant/config.json` inside the Godot project, outside version control:

```json
{"source":"ABSOLUTE_PATH_TO_EXISTING_GODOT/content/zones", "python":"ABSOLUTE_PATH_TO/python.exe", "libs":"OPTIONAL_LOCAL_PYTHON_LIBRARY_DIRECTORY"}
```

Python requires numpy and Pillow. `libs` is passed as an extra Python module directory; it can be empty when these are installed in that Python. Use the existing matching Godot Mono engine/runtime, then run `--path PROJECT --script res://enhanced/replant/panel.gd`. No server is started. A prepared Windows launcher is supplied with the local deliverable.

The development checkout contains only the previously copied Connacht art. The panel previews other zones by reading their absolute source directories; it does not duplicate all converted game content. The normal game's integration hook consumes active plans for content available in that development project. This is not a deployment to the installed playable client.

## Workflow

Scan, select a zone, prepare that zone or all eligible Hibernia, choose a preview point on the map, then open the 3D A/B view. WASD moves, Q/E changes height, right mouse looks, Space switches original/replanted without changing camera or light. The map's right click adds an exclusion circle; prepare again to save it. New preparation replaces the *latest candidate bundle*, not an active bundle. Preparing only one zone creates a one-zone candidate; activating it replaces the previous active package rather than merging packages.

Activation validates the manifest, per-zone plans, masks and source hashes before replacing a local pointer. Restart/reload a view or game zone to read a changed active pointer. Rollback swaps back the previous pointer, validating its resources first; restoring original disables the overlay. History is appended locally. Originals need no restoration because they are not overwritten. Windows atomic replacements retry brief sharing violations from panel readers.

## Placement and runtime

Classic and SI use different clutter group mappings. The planner preserves water/reed, rock and snow groups, applies water height/mask checks, slope limits, conservative named building buffers and explicit road-material exclusions. Roads painted into a whole-zone colour texture cannot reliably be inferred by texture names: original density masks and visual/manual exclusions remain necessary. The masks are rules, not a claim of visual approval of every zone.

The runtime checks surface collision and slope again; original seed/tall grass is always retained. Named low grass and unwanted undergrowth are replaced only in cells with successfully generated new plants. Rocks, debris and unsupported areas retain original clutter. Geometry uses the approved procedural plant catalog. Original terrain materials stay intact. Original vegetation reappears in A/B, unsupported zones, stale/hash-invalid plans or when the overlay is disabled.

New vegetation streams in at most nine 32 m chunks around the viewer, with stable per-zone/chunk seeds, one nearest missing chunk per frame, a per-chunk instance cap and distance fading. Nodes follow zone-local coordinates, including world offsets. Existing grass visibility/density settings also apply. The dense default is 24 candidates/m2, capped at 20,000 groups per chunk; it can cause loading/rebuild hitches and needs optimization and traversal profiling. Lower the density/cap for lighter hardware. Three butterflies and two bees at most per loaded zone follow nearby real flower instances; there are none if that patch has no flowers.

## Verification

`verify_prepared.py --state STATE --libs LIBS --work SCRATCH --report REPORT.json` checks a complete prepared 21-zone v0.37c Hibernia package: source/output hashes, region guard, eligible groups and mask agreement, corrupted/rehashed invalid manifests, stale source rejection, manual exclusions, activation/disable/rollback in a scratch state and unchanged real activation state. It does not start a server. Scratch outputs remain under the supplied work directory.

The accompanying report separates these automated checks from actual rendered A/B samples in Connacht, Domnann and Bog of Cullen. Full Hibernia traversal, 4K performance across zones, multiplayer/gamebot load, biome transition tuning and all building/road exclusions remain unreviewed. Existing engine render-thread/image warnings are recorded in logs rather than hidden. No release/publication is performed by this tool.
