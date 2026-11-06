# Bounded live stable transport

The original server consumes the ticket, creates the actual route horse, sends Riding0xC8, controls its path/speed and acknowledges dismount. Unreal displays the original horse and ride_horse pose and places the rider on the currently posed, instance-scaled saddle. Walking/run lock/target tracking cannot move the mounted rider independently. Space and /dismount use the original client request; neither invents a successful unmount.

Only Carsten's Ticket to Druim Ligen is currently enabled. Its original21-point, approximately2180m itinerary stays inside the loaded Connacht zone and has completed the real-server QA route. The other five offered itineraries leave the available world. They remain visible but disabled in the original merchant window, and the inventory command path rejects purchase before Target/BuyItem. No server ticket, price or route is rewritten. Ordinary merchants retain their existing path.

The route uses template313/model448 (Speckled Horse), independently of standing horse2174. Missing original448 assets are added in a new plugin namespace; all existing model catalogue entries must remain identical. Prepared single-passenger slot0 only; personal mounts, boats, multiple seats and unrestricted cross-zone transport are outside this package.

Original sound-set41 supplies four unchanged WAVs. Hoof triggers come from the original Godot bone-contact helper, following actual clip playback and speed/instance-adjusted stride. Human footsteps are suppressed while mounted. The shared mixer applies master/effects volume. No new hoof trigger is produced after dismount.

Evidence distinguishes source2174 axis calibration (<0.000052cm) from448 node-rest versus imported skin-reference differences (maximum0.9996cm, spine-anchor0.1863cm). Native seat tests independently retain the source saddle point using the actual imported reference and posed bone, including scale factors0.96/1/1.3. There is no guessed constant saddle height.

Required installation evidence:

- 68 state checks,8 gateway checks,29 coverage/purchase checks and35 existing inventory checks.
- 64 native assets/saddle/stride checks.
- 265 prior audio/interface checks; movement53, jump9, tracking35 and original water mask65559 checks on the same candidate binary.
- Completed current-build original route and actual native Space-input tests, with hoof PCM consumption, grounded collision, post-dismount silence, normal exits and restoration of the marked private database.

The installer previews by default. Applying it requires the normal client/server ports free, verifies current source/resource/proof hashes, backs up each replaced file, records all new namespace files and verifies the complete predecessor/successor chain. Its rollback refuses to overwrite files changed after this delivery. Player saves, server rules, original archives and WORK maps are outside the write set.

Reproduction tools are beside this document: audit_live_riding.py, prepare_live_riding_content.py, run_live_riding_import.py, prepare_live_riding_data.py, prepare_live_riding_audio.py, prepare_live_travel_routes.py; verify_live_riding_state.py, verify_live_riding_gateway.py, verify_live_travel_routes.py, verify_live_riding_assets.py, verify_live_riding_regressions.py and verify_live_riding_movement_regressions.py. verify_door_audio_real.py accepts --native --live-riding with either --riding-full-route or --riding-space, using only the existing marked disposable server. install_live_riding.py accepts --workspace, --apply and --rollback.

Installation receipt and owner checklist determine delivery state. Automated evidence does not substitute for the owner's visual, gameplay or listening review, and this block does not mean the entire client migration is complete.
