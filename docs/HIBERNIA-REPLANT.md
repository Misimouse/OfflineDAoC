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

The runtime checks surface collision and slope again; original seed/tall grass is always retained. Unwanted named shrubs are hidden throughout eligible planned habitat, independently of replacement parcel readiness. Named low grass remains visible on a first visit until new plants succeed in its cell; that coverage is remembered until the overlay is reset, so unloading/rebuilding a parcel cannot resurrect replaced low grass. Rocks, debris and unsupported areas retain original clutter. Geometry uses the approved procedural plant catalog. Original terrain materials stay intact. Original vegetation reappears in A/B, unsupported zones, stale/hash-invalid plans or when the overlay is disabled.

The playing client loads prepared placement resources in at most nine 32 m chunks. It never generates new candidates or performs placement physics queries during play (`allow_generation` defaults to false). Transform uploads retain the 6 ms frame budget. Missing/corrupt/unprepared parcels retain stock vegetation, including shrubs, instead of silently starting expensive generation. Readiness and session coverage still control replacement of the stock low grass. Source atlas UV0 and wind weights are retained; A/B cancels pending uploads and restores originals.

`bake_check.gd` is the offline preparation utility, initially bounded to Ardee (x chunks 36..45, z 35..42). It explicitly enables candidate generation and real terrain/scenery collision checks, then saves plain variant data with no executable objects. The native panel separates map preparation from **Preparar plantas de Ardee**. Other Hibernia plans are still masks, not a claim that all their placement resources are prepared. No ToA/other realm generation occurs.

Prepared resources are private/ignored under `.enhanced-session/replant/cache`. Keys include the plan, effective density, generator, plant catalog, zone loader, engine and local model glTF/bin/JSON hashes. Files are validated for key, chunk, shape, finite transforms, accepted count and cell bounds. Each file is capped at 4 MiB; the development cache retains at most 256 parcels across namespaces. This is a bounded Ardee pilot, not the final asset packaging/storage policy for all Hibernia. Only nine parcels are active in the client. Changing density or relevant source files requires re-preparation.
Nodes follow zone-local coordinates, including world offsets. Existing grass visibility/density settings also apply. The dense default is 24 candidates/m2, capped at 20,000 groups per chunk. Lower the density/cap for lighter hardware. Three butterflies and two bees at most per loaded zone follow nearby real flower instances; there are none if that patch has no flowers. Unprepared locations retain original vegetation. At prepared locations only file reads and rendering uploads remain during play.

## Verification

`verify_prepared.py --state STATE --libs LIBS --work SCRATCH --report REPORT.json` checks a complete prepared 21-zone v0.37c Hibernia package: source/output hashes, region guard, eligible groups and mask agreement, corrupted/rehashed invalid manifests, stale source rejection, manual exclusions, activation/disable/rollback in a scratch state and unchanged real activation state. It does not start a server. Scratch outputs remain under the supplied work directory.

The accompanying report separates these automated checks from actual rendered A/B samples in Connacht, Domnann and Bog of Cullen. Full Hibernia traversal, 4K performance across zones, multiplayer/gamebot load, biome transition tuning and all building/road exclusions remain unreviewed. Existing engine render-thread/image warnings are recorded in logs rather than hidden. No release/publication is performed by this tool.

`traversal_check.gd` measures headless CPU frame times after all nine parcels settle, then follows a 72 m route at 4 m/s. `fingerprint_check.gd` hashes every transform and custom colour by species/chunk, with optional `--npc-picks=true --toggle=true` checks. The local 20 October comparison retained exactly 148,321 groups and all nine hashes. Walking's worst frame fell from 481.654 ms to 37.419 ms, with frames above 50 ms falling from six to zero; initial full coverage rose from 5.744 s to 17.360 s. These are one machine's CPU results, not GPU FPS promises. Rendered captures wait for `is_settled()` instead of measuring partially filled patches.


### Revisit regression (20 October)

`revisit_check.gd --bundle=ABSOLUTE_BUNDLE --out=ABSOLUTE_OUTPUT` renders production alpha/metadata with white test cards and unshaded lighting. Its six stages cover original, first arrival, ready, parcel unload at 40 m, reconstructed return, and original again. Shrubs stay suppressed before replacement completion; replaced low grass stays suppressed after parcel unload/rebuild; tall vegetation survives every stage; disabling clears remembered coverage. The placement fingerprint remains identical for all nine chunks (148,321 instances), including NPC pick volumes and pending-job A/B cancellation.

This earlier revision fixed overlay-driven resurrection of discarded stock vegetation. At that stage revisited parcels still regenerated incrementally; the prepared-resource pilot below supersedes that behavior. Upstream model/texture loading is separate. Low grass fallback is limited to not-yet-replaced cells; A/B or reloading the zone resets coverage. Full in-game repeat traversal still needs observation. Standalone shader captures and headless CPU measurements are separate evidence, not a gameplay completion claim.


### Prepared Ardee loading pilot (20 October)

The supplied local positions are 52096/49249 and 51026/48658 (DAoC zone units, divided by 40 for Godot metres). **Scope: loading only.** The existing active/latest bundle and its density/habitat masks are unchanged. The ground-matching experiment was parked without activation at the owner's request; distribution, terrain textures and the existing 35â€“50 m detail fade remain unchanged. The Ardee preparer covers 80 parcels around the approved preview and the supplied positions; it does not claim all Hibernia resources have been built.

`prepared_check.gd` checks both supplied positions, an unprepared location and return, asserts that every playing-client upload came from prepared data, and tests stock fallback/A-B. The existing approved nine-chunk fingerprint remains exactly 148,321 instances with all nine transform/colour hashes equal after preparation and cached reload. This validates identical placement, not new terrain distribution.

Prepared-data file reads and GPU uploads can still produce small stalls; no GPU FPS or zero-pop-in guarantee is made. Far/mid-distance vegetation, a final Hibernia resource package and biome/road distribution are deferred. The development cache's 256-parcel limit is sufficient for this pilot; packaging all Hibernia must not reuse that eviction policy as its permanent asset store.

With the original masks, the final headless 72 m walking check filled nine parcels in 1.320 s (earlier generation path: 19.715 s); walking max CPU interval was 32.466 ms, p95 16.727 ms, zero intervals above 50 ms. The supplied locations loaded in 0.671 s and 0.430 s, with return in 0.666 s. These are placement loading/CPU checks, excluding zone startup and server login, not GPU FPS or complete client startup benchmarks.
