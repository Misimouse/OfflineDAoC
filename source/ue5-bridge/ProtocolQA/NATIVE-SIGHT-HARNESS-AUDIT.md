# Grounded native sight harness

The earlier casting fixture placed the ordinary character below the sampled
terrain at its old saved coordinates. The dedicated harness now reuses the
configured playable spawn, samples the original257x257 height field with its
triangle interpolation, and places only disposable QA characters10cm above it.
Native capsule physics settles the character onto actual map collision.

The relay uses the configured project/map and optional environment/foliage
catalogues from the normal launcher. Native startup polls a bounded300-second
connection deadline and closes its own process/listener/log on startup failure.
An explicit headless_geometry option uses UE NullRHI while retaining the real
world, collision queries and capsule physics. Rendered callers keep D3D11.
Eighteen isolated startup-failure checks cover modes, arguments and cleanup.

The dedicated ordinary-server run passes28 checks: earned level/training,
retained quickbar healing and power use, repeat healing, the new Nurture buff,
ten correlated real UE sight replies, grounded placement and saved logout.
The actual map is Ardee_Nwiro_Prueba_Limpieza_v01. Active navigation sampling
reports floor/grounded true,11 blocked structure samples,172 trunk samples and
183 capsule/camera sweep samples. This remains sampling, not all-map certification.
Native, both ordinary clients and server exit normally. Private DB/libraries
are restored; native/server runtime hashes are unchanged. No WORK assets or
played data are replaced.

Earlier rendered attempts remain failed evidence. Under-terrain captures are
not accepted visual evidence. After grounded placement, multi-second rendering
frames prevented timely LOS replies; NullRHI allows the original1500ms deadline
to remain unchanged. This is a QA harness fix, not a graphics/performance fix or
rendered spell/menu/art acceptance. Separate positive close-target and sampled
navigation checks do not certify every wall, door or tree.

Private evidence: NativeSightHarnessLab. Reproduce with
DAOC_PROGRESSION_TRAINING=cast, DAOC_PROGRESSION_GODOT=installed and
DAOC_NATIVE_SIGHT_HARNESS=1 in the marked private runtime.
