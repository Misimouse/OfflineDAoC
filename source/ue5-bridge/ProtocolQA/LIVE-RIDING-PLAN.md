# Live stable transport: bounded delivery

Status: installed on6November; owner gameplay and listening review remain pending. This closes the single-zone live riding package, not the entire client migration or unrestricted world travel. See LIVE-RIDING-DELIVERY.md for reproduction and scope.

The server remains authoritative for ticket consumption, actual horse identity/size, mount acknowledgement, route, speed and dismount acknowledgement. The separate offline HorseRoutes controller is not substituted into a connected session. Original live route tickets and paths remain unchanged.

The actual Carsten ticket HR_TirNaNog_DruimLigen uses template313/model448, rather than standing stable horse2174. The original missing448 mesh, materials and animations were added in a new namespace, preserving every existing model entry. Native saddle placement follows the actual posed bone and instance transform. Rider animation uses original ride_horse; native input cannot walk the rider independently. Space and /dismount send the original request and wait for its acknowledgement.

Only the completed original21-point, approximately2180m itinerary is enabled. Five offered itineraries leave the currently loaded Connacht zone. The original shop shows those destinations unavailable, and the inventory command path rejects purchase before network transmission. Unknown or changed ticket/stable definitions cannot silently enable travel. No fabricated route, altered price, path rewrite or owner DB edit.

The original sound-set41 supplies four byte-identical WAVs. Original Godot bone-contact timing drives native hoof sounds at the actual clip/stride rate. Master and effects volume apply. Human footsteps are suppressed while riding; hoof contact generation stops after dismount. Only prepared single-passenger slot0 is supported.

Completed evidence:

- 68 isolated Riding-state checks,8 gateway checks,29 travel catalogue/inventory checks and35 existing inventory checks.
- 64 native asset/saddle/stride checks, including all13 original playable ride clips and actual size factors0.96/1/1.3.
- 265 previous audio/interface checks on the private candidate; walking53, jump9, target tracking35 and original water sampling65559 checks on the same binary.
- Current-build full original server itinerary: Reports/live_riding_real_protocol/20261106-232432-545801/verified.json.
- Current-build original ticket purchase, unsupported-ticket rejection, hoof PCM, actual native Space input and grounded/silent dismount: Reports/live_riding_real_protocol/20261106-233037-523164/verified.json.
- Both real trials ended normally and restored the marked disposable database. Failed earlier attempts remain failed and were retained; the long-route QA profile now explicitly allows sufficient runtime and waits for its real duration.
- Installation preview passed,60files installed,12 replaced files backed up, exact predecessor/successor file validation passed, and repeat installation returned already_current. Installed-client audio/UI regression results are kept separately.

Source2174 axis calibration agrees within0.000052cm. Source448 node-rest versus imported skin reference differs by at most0.9996cm (spine anchor0.1863cm); that is recorded separately, not falsely described as exact. Independent native tests retain the source saddle point with the actual imported and posed reference under rotation, translation and instance scale. No guessed saddle-height fallback.

Receipt: LiveRidingLab/installed.json. Backup: Backups/LiveRiding_20261106-234604-348155. Native DLL SHA256: eb2113ff0633cdb150a78ed2090934f405cc75497d5cf501f9f16aecf2f3bb01. Original archives, normal server data and WORK maps were not modified.

Remaining scope: owner review; unrestricted cross-zone stable routes require more loaded world and explicit transition coverage. Personal mounts, boats, multiple seats and broader NPC travel are not claimed. The next main integration block is CLIENT-CONTROLS, using the original editable keybind/settings UI as reference.
