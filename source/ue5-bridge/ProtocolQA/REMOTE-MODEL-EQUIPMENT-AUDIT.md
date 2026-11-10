# Native remote player-form equipment

Installed a three-file native successor: plugin DLL, module manifest and `DAoCBridgeEquipment.cpp`. No map, art, database, backend, gameplay rules or UI replacement.

Per-frame replay of the real ordinary Bainshee observer trace reproduced two weapon components remaining attached during the form. The initial single-frame probe timed out during cold loading and was rejected as evidence; the corrected probe streams snapshots continuously like the actual gateway.

Remote equipment presentation now uses the catalogue's explicit known race/body distinction, matching local player-form presentation. A known non-race player form releases its attached weapons. The original equipment data remains untouched, and returning to a race figure rebuilds the correct attachments. NPCs and unknown classifications retain existing handling.

Candidate and installed per-frame probes verify: original race body has two weapon bindings; Bainshee models 1883,1884,1885 have zero; return restores both; an NPC using the form body still has both. Only the Celt form sequence is from a real two-player cast/timer; the other two forms and NPC are explicit native policy controls. Ninety-five additional equipment checks pass against the candidate, covering existing player/NPC attachment paths. Eleven guard checks reject invalid deployment plans. The full installed receipt chain passes after replacement.

This closes the bounded native attachment defect with owner review pending. The probes use NullRHI and do not certify rendered materials, visual quality, every possible class form, every weapon or battle-scale performance. Existing local transformation, original ordinary server rules and WORK assets remain intact.
