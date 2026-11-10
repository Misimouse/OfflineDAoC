# Original quest reward transport

The inactive 1.127 reader and request encoder passed 265 checks. An isolated server using its original quest handlers then passed 14 connected checks with disposable ordinary accounts and a synthetic quest row. This validates the protocol, not an import of additional world quests.

The original packet capture showed that quest rewards use slotless item records. The offer response uses DialogResponse 0x82 / QuestSubscribe 0x64; the reward choice uses literal opcode 0x40. 0xE8 is the historical pre-XOR value, not the opcode this client sends.

The connected run verified decline, journal entry on accept, the separate reward window, rejection of an invalid choice and an unrelated account, the exact selected item and money, the original fixed stack, no duplicate grant, and persistence on logout. The private backend, server and database were restored. The normal client and server were unchanged.

Next: bind responses to the current NPC and dialog, reconcile them with the original journal, then connect the original dialog UI and verify the full path before installation.
