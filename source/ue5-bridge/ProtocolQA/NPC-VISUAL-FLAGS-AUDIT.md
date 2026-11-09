# NPC ghost appearance: audit and private state candidate

The original production NPC-create packet carries ghost in flag 0x01. Godot applies a front-surface depth pass plus translucent original textures and a subtle cool-white rim. Monster opacity is 0.5; Catacombs race-figure opacity is 0.9, retaining skin/dye color and hair coverage. Original equipment is ghosted too. This is distinct from local-player stealth and must not reuse its gray/0.45 presentation.

The adapter currently retains realm/flying/name/targeting but drops the ghost rendering contract. NPC movement flags encode zone information and cannot replace create flags. Original NPC TORCH is separately normalized to database bit0x40; the original NPC view does not create a personal-light source from it, so the audit does not authorize adding NPC or building illumination.

`verify_npc_visual_flags.py` extracts the original Godot normalization block unchanged and compares all 256 first-byte combinations against representative second-byte states. The 1,815 candidate checks also cover malformed bytes, unrelated movement/player packets, reused identities, missing create data and copied-state isolation. Candidate metadata remains disconnected and uninstalled until a proper native material path passes rendered acceptance.

A read-only local population survey found ghost flags in existing world data, including models without exported native bodies and a Wisp whose effect is the body. Do not treat those as generic opaque figures or declare ghost appearance complete from flag tests. Private source exports use an original Zombie and Celt race figure as representative comparisons; world population imports remain separate.
