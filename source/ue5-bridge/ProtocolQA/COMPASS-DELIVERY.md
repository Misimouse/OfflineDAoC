# Original compass integration

The native world interface now supports the original compass strip. Its heading follows the character, so orbiting the camera does not change north. The original image is copied byte for byte from the installed client; converted stock content stays outside Git.

- Ctrl+C toggles the compass and is editable in the existing key configuration.
- Esc → Windows → Compass restores a hidden compass.
- Drag the compass to move it. Position and visibility are saved per character.
- Reset Window Layout restores its initial position above the quickbars.
- The compass uses the existing interface scale and viewport layout and blocks clicks from reaching world targets.
- The character selection screens do not display it.

Reference: the installed Godot `game/ui/game_ui.gd`, `content/ui/keybinds.json`, and `game/net/server.gd`. The native coordinate conversion preserves the original server heading convention. No server packet, database, gameplay rule or transport action is added.

Verification uses a separate CompassLab build, the actual Slate window, original artwork, cardinal and intermediate headings, north wrap, camera orbit, visibility, layout reconstruction, reset, pointer blocking and drag capture. A rendered compass image is retained for visual review. Earlier native packages, including the real positive-HP/zero-percent snapshot, are checked against the same build. These are automated checks, not owner gameplay acceptance.

Installation is restricted to the listed native files and original compass image, with predecessor hashes, evidence hashes, exact backups and rollback. Historical delivery evidence is preserved. The normal launcher is unchanged.

Owner review: turn the character through north/east/south/west, orbit without turning the character, toggle Ctrl+C, move the compass, reopen it from Windows, re-enter the character, and check it at different interface sizes. Owner acceptance remains pending.
