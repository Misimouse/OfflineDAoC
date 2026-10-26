# Approved Hibernia artwork

`connacht-20261026` is the owner's approved visual checkpoint, including the canvas, fence,
Muire entrance and night effects approved on 26 October. It contains the runtime profiles,
textures, scenes, generated geometry, shaders and supporting source assets needed by those profiles.
The snapshot contains 1,244 runtime files, including the 73 previously approved Connacht texture overrides (about 2.17 GiB compressed / 2.77 GiB installed).
It does not include accounts, passwords, databases, saves, logs, Godot import caches or a game server.

## Build and install from a checkout

1. Install Python 3.10+, .NET 10 SDK and Godot 4.7.2 **.NET**.
2. Supply the converted v0.37c base content in `source/new-client/godot/content`, keeping
   `content/.gdignore`. At minimum this checkpoint needs Connacht (207), Tir na Nog (209),
   their shared models/textures, character data and sounds. Use a matching v0.37c installation
   or the conversion pipeline described in the [client README](../README.md).
3. From `source/new-client`, run `tools/build_csharp.ps1`. The build installs the approved
   resource package automatically before compiling C#. Run this in a clean checkout;
   the installer refuses to overwrite a different private LAB profile.
4. Start your separately configured game server, then run the client as described in the client
   README. The normal zone viewer applies the installed artwork automatically. No LAB account,
   private login script, developer mode, absolute machine path or test server port is required.

Downloading source alone does not supply the original game's converted content (approximately
33 GB). The original-content prerequisite already existed; this directory supplies the approved
improvements that were previously only on the developer's computer.

## Manual installation, verification and rollback

From `source/new-client`:

```
python tools/install_approved.py                 # preview
python tools/install_approved.py --apply         # install into this checkout's godot/
python tools/install_approved.py --verify        # verify every installed file
python tools/install_approved.py --rollback      # remove only files created by this installer
```

`--project PATH` selects another Godot project. All payload files are confined to its
`.enhanced-session` directory. Installation verifies the entire payload before writing anything,
refuses conflicting files, and activates the package last. Rollback refuses to erase later edits.
It never alters stock content or player data. The receipt and activation marker are local files.

The historical directory names are retained because embedded Godot scenes reference them.
They are runtime resources, not user sessions. All resource references in text profiles use
`res://`; the original LAB has not been rewritten to create this snapshot.

## Storage and scope

The manifest lists each unpacked file, its SHA-256, byte length and compressed chunks. Chunks
are zlib-compressed, deduplicated by content and split below GitHub's individual file limit.
They are ordinary Git files: a clone or source ZIP includes the complete package without LFS
or a separately authenticated download. Preserve the manifest and all `blobs` files together.

The approved art was built from owner-selected/generated artwork, procedural geometry and
modified/converted DAoC materials. Original game sounds and derivative models still inherit
their source rights; this snapshot does not grant a new license to the underlying game assets.
It is a reproducible backup and source-build installation, not a published game release.

Connacht and the capital are the verified visual scope. Matching Hibernian model families use
the shared controllers in loaded zones; this is not a claim that every interior or every zone
has been converted or visually reviewed. The requested stronger water waves, shore flora and
reactive fish are subsequent work and are not part of this approved checkpoint.

## Validation

Installer checks: corruption rejection, path confinement, collision preservation, idempotence,
verification and guarded rollback. Godot checks run from a separately located project installed
only from this package, using a read-only reference to the matching base content. They cover
resource hashes, controller configuration, rendering and restoration. No server is launched
by the installer or these checks; user approvals remain separate from automated checks.
