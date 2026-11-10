# Ordinary cast movement and recovery roundtrip

The installed client passes30 overlapping ordinary-server/UE checks. A retained
level-two Naturalist heal attempted with repeated movement input receives the
original server interruption and consumes no power. Starting stationary, then
moving during preparation, also interrupts without power cost. Stopping permits
normal healing again, including actual recipient health gain, power cost,
repeat use and the newly learned Nurture buff.

The server may first emit CastAnimation then InterruptAnimation. The test checks
the authoritative cancelled result instead of inventing a no-animation rule.
The original SpellHandler.CasterMoves retains instrument/MoveCast exemptions;
instant spells and those exemptions are not overridden or exhaustively retested
by this ordinary-heal case. Existing class-specific evidence stays separate.

UE runs real physics and sight queries with NullRHI on the configured map and
grounded disposable spawn. No synthetic sight approval is used. Cleanup sends
zero movement before normal logout, including on failed fixture assertions, so
a still-walking QA character cannot indefinitely refuse saved logout. The
passing run has normal native/client/server exits, restored private DB/libraries
and unchanged normal native/server runtime hashes. No runtime deployment is
required. Private proof: SpellMovementRoundtripLab. Owner review remains pending.

Reproduce the grounded cast harness with DAOC_CAST_MOVEMENT_PROBE=1 in addition
to DAOC_NATIVE_SIGHT_HARNESS=1 and DAOC_PROGRESSION_TRAINING=cast.
