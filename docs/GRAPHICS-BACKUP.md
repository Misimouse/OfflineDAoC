# Godot graphics branch and private asset archive

Our client fork is [Misimouse/OfflineDAoC](https://github.com/Misimouse/OfflineDAoC),
based on [shadowofze/OfflineDAoC](https://github.com/shadowofze/OfflineDAoC).
The Godot client lives in `source/new-client/godot`; this is not a fork of the Godot engine.
Our graphics work is on **enhanced/graphics-v0.37c**. `main` and the upstream release branches
are kept separate. This graphics branch is still based on the 0.37c client, not rebased onto 0.38.

| Feature | Runtime / source | Current status |
|---|---|---|
| Water | `enhanced/terrain/water_trial.gd`, `water_trial.gdshader`, preparation/build scripts | User accepted the natural waves; opacity deferred to final corrections |
| Elms | `enhanced/trees/elm_trial.gd`, `prepare_elm.gd` | Shared 661-tree model repaired for root contact and photographed bark; owner visual review, foliage and LOD refinement remain |
| Ground and paths | `enhanced/terrain/paths_pbr.gd`, `paths_pbr.gdshader` | Four-patch material trial; broader soil redistribution remains |
| Monoliths and ivy | `enhanced/terrain/stone_ivy_trial.gd`, build/prepare scripts, shaders | Geometry trial accepted; stone and leaf textures need final refinement |
| Replanting | `enhanced/replant`, `landscape_patch.gd` | Reversible Hibernia plans; active and most recent prepared plans differ |
| Inspector / Forge | `enhanced/godot_tools`, material loaders | Adapted resource inspection and reversible image overrides |

The matching GLB, PNGs, baked Godot scenes/meshes, active manifests and imported validated
Ardee images are archived privately in **Misimouse/DAoC-Godot-Remasters**, under
`graphics/zone207/snapshot-20261022`. They are not missing because art is unfinished:
work in progress is backed up with its status explicitly recorded.

The subsequent elm correction is kept separately in `graphics/zone207/elm-repair-20261022`,
with its new scene, bark maps, checksums and prior activation for rollback.
See [ELM-REPAIR-20261022.md](ELM-REPAIR-20261022.md) for the measured root gap and checks.

This public code branch excludes converted stock game content, binaries, credentials,
accounts, played databases, logs and private activation folders. The private archive has
a file inventory with SHA-256 and exact project-relative recovery destinations. The base
converted client content must come from the user's existing installation.

Tool applications (Forge, Inspector, LAB) have their own private source repository,
**Misimouse/DAoC-Godot-Toolkit**. Forge's approved-image registry remains separate from
the graphics snapshot: archiving an experiment does not automatically approve its art.

No game server is started or restarted by this backup operation. See the individual
ELM-TRIAL, WATER-TRIAL, STONE-IVY-TRIAL and HIBERNIA-REPLANT documents for earlier checks
and their limitations; this snapshot does not turn them into release certification.
