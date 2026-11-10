# Remote ModelChange size semantics

Installed one adapter file. Original `PacketLib168.SendModelChange` sends size zero for players; the adapter previously overwrote the current size with zero. UE then clamped the rendered scale near zero. The same problem affected return to the original race model.

The model-change branch now retains the existing size when the packet carries zero. Explicit nonzero size changes remain authoritative, including NPC model-and-size updates. It preserves the current equipment revision and does not create a living from an unknown OID. No server, native binary, database or map change.

The pre-fix private regression failed three size-retention checks. The correction passes 11 scoped event checks, 69 existing remote-player checks and 25 existing local-model checks; all 105 also pass against a private copy of the installed adapter. Original source contract and event-state tests establish this bounded correction. They do not establish a real two-player transformation or native restoration for every model and equipment combination.

Exact proof hashes, unchanged native identity, one-file plan, exclusive normal-port guards, verified backup and automatic rollback protect installation. The installed receipt participates in the existing successor chain; predecessor inventory rollback is refused while this dependent delivery remains installed. Owner acceptance stays pending. Continue remote model/equipment restoration separately before claiming full multiplayer transformation coverage.

Subsequent bounded follow-up: `REMOTE-MODEL-ROUNDTRIP-AUDIT.md` records 25 ordinary two-player checks and 34 installed UE actor-replay checks. Native per-frame equipment attachment and visual acceptance remain explicit separate gates.
