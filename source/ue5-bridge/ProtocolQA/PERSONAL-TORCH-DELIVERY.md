# Personal torch delivery

The bridge now carries the original personal-light state through Position and Heading action bit 0x80. Shift+T is editable in Controls and preserves Training T. Existing saved key assignments take precedence over the new default. The enabled preference is merged into existing controls settings and synchronized on character entry.

Original Godot references: game/player.gd, game/zone_loader.gd and game/sky_system.gd. The light is white, 3.2 metres above the figure origin, with a 30 metre attenuation radius and no shadows. Day/dawn/dusk/night and the original moving server storm band determine the energy factor. Unreal uses an explicit 600 lumen maximum, scaled from 0.15 to 1; engine energy numbers are not assumed interchangeable. Nearby peer lights use server-confirmed flags, a 60 metre activation distance and a maximum of 16 sources. Missing metadata, logout, lobby, removal and connection loss remove lights.

Validation: 1,502 state comparisons against the original sky function; 261 gateway, 8 riding and 69 remote-state checks; 23 real isolated checks with two ordinary accounts; 19 native torch, 55 pose, 25 combat and 387 NPC-motion checks; 260 actual controls checks. Private rendered captures cover off/day/night without clipping in the captured figure. Installation has exact file hashes, 46 damaged-delivery simulation checks, recovery copies and full predecessor-chain verification. These are automated and private render checks; owner gameplay acceptance remains pending.

This delivery does not change world/building lights, character materials, terrain, server rules or played databases. NPC-create torch bit 0x04 has a different meaning from player actions and NPC-movement flags; it is a separate audit.

Owner checks when convenient: Shift+T on/off; T still opens training; remap torch in Esc Controls; toggle off, /quit, re-enter and verify it stays off; inspect daylight/night brightness; if a second client is available, verify the other player's light follows its toggle. All interface text stays English.
