# Original local jump and landing packets

Space jumps when the player is alive, standing, able to move and outside text/options input. The local native pawn uses the original Godot jump speed (4.6 m/s) and gravity (18 m/s2). The original jump clip is requested while rising or after 0.15 seconds airborne, without looping the clamped animation. Existing death, posture and cast/action priorities remain in the pose controller.

UE clears vertical velocity when entering walking mode. The native character now captures downward velocity in `Landed` before that reset and retains it until the next outgoing movement command. The bridge's existing original Position API receives a negative vertical speed and ground bit once. Teleports clear a pending landing. Flight flags are not introduced. Server fall-damage eligibility, SafeFall and damage calculation are unchanged; privileged GM characters remain exempt according to existing server rules.

## Acceptance

- Transient box-floor native physics: nine checks; actual jump apex approximately 61 cm, nine-metre fall impact approximately 18 m/s. Initial fixture runs fell through an unsuitable mesh floor; those failures are retained, and the explicit box fixture passed.
- Disposable real protocol: actual native jump produces airborne movement, exactly one ground packet retaining jump impact speed, then ordinary zero vertical speed. A real nine-metre drop sends impact speed below -15 m/s with the ground flag.
- The real protocol witness uses the private protected GM. It verifies delivery of impact data, not health loss for a normal player.
- 265 existing audio, UI and selection regressions pass against the candidate.
- The same candidate must pass surface swimming/stopping/return, the actual river bridge deck, and acknowledged closed/open door crossing/return before installation.
- All protocol sessions restore the marked test database and close normally. Owner characters and map assets are untouched.

## Delivery

`install_jump_landing.py` gates the exact predecessor, compiled source hashes, physics proof and three real protocol routes. It records eight explicit native files, including one new acceptance source, with a backup and rollback. The normal server/client must be closed. The original Godot gateway and server rules are reused without replacement in this delivery.

## Owner checks

Use Space while standing and running. Check the airborne pose and landing, then try Space while sitting, dead and typing: it must not jump. Repeat ordinary stairs, a door, river entry/exit and the bridge. On an appropriate ordinary test character, verify a safe jump does no damage and a sufficiently high fall follows the server's rules. GM protection can prevent fall damage. This block does not add climbing, diving or a keybinding options page.
