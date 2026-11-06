# Visible-body target selection

The previous cursor test used a circle around the root component's projected
center, capped at 90 pixels. A nearby or tall character could visibly extend
well above that circle, forcing clicks toward its waist or legs.

Selection now projects the full visible body bounds, including visible body
mesh components, after their actual transforms and scale. Hidden components,
equipped weapons, particles and nameplates do not enlarge the picking area.
Small targets retain modest pixel tolerance. Character movement capsules,
model scale, server size and animation remain unchanged. Existing targetable,
dead, range and line-of-sight checks still apply. Tab enemy cycling retains
its existing range and rules.

The native acceptance fixture deliberately gives a character a short root
mesh and a much taller visible child. It verifies upper/lower-body picking,
rejection outside the body, hidden/equipment exclusion, dead/untargetable
rejection and unchanged physical collision. It runs in UE with an actual
camera and viewport projection, without a server or owner login.

## Delivery and checks

- Private candidate: 15 selection, 14 combat audio and 15 spell audio checks.
- Installed normal client: the same 44 checks pass, including real audio PCM
  consumption. No server is started for these checks.
- Fourteen synthetic receipt-chain checks reject altered predecessor hashes,
  binaries and unchanged original sounds. All four client installers remain
  idempotent after installation.
- `install_target_selection.py` backs up and replaces exactly two native
  binary/module files and three matching plugin source files. Hash checks,
  normal-session port guards and rollback preserve accepted predecessor
  deliveries and leave the database untouched.

Private proofs and backups stay under `TargetSelectionLab` and `Backups`;
they are not published. Owner acceptance in an actual session is pending:
click the head, upper torso and legs of tall/short NPCs and mobs, select
yourself, change targets, and confirm walls and Tab range still behave as
before. This fixes picking, not a claimed correction of original race height.

Shar remains disabled in normal character creation pending its own complete
acceptance. The menu-of-options/volume request is recorded separately; neither
is silently included in this selection patch. Previously tested sounds have
owner confirmation; volume-control acceptance remains pending that menu.
