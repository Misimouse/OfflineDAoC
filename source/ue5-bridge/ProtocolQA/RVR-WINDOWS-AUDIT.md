# Realm war window: source audit and bounded delivery plan

This block migrates the existing realm-war information window. It does not
create frontier maps, enable teleportation or change siege/gameplay rules.
Frontier rendering, resource budgets and large-battle optimization remain a
separate owner requirement.

Existing implementations to reuse:

- Original Godot `game/ui/warmap_window.gd`: realm tabs, original map tiles,
  keep/relic/battle icons, Update and frontier player position.
- Original `content/ui/warmap/warmap.json` and its PNG atlases: existing map
  geometry, labels and positions; no replacement design is needed.
- Original `DaocClient.ShowWarmap`: original packet 0x48. Request code 0 sets
  the page, then code 1 asks for its keep ownership and battle information.
- Original decoded `warmap_keeps` (0x49) and `warmap_fights` (0x4A) events
  already reach the original server's `world` signal.
- DOL `WarmapShowRequestHandler`, `KeepManager.GetKeepsByRealmMap`,
  `PacketLib1115.SendWarmapUpdate` and `WarMapMgr.SendFightInfo` provide the
  authoritative fields and request behavior.

Verified details that must survive integration:

1. Pages are **1 Albion, 2 Midgard, 3 Hibernia** in the current original window
   and keep manager. The older comment above `DaocClient.ShowWarmap` says 0–2;
   follow the actual implementations, not that comment.
2. Keep identity is `(decoded_map + 1) * 25 + index + tower * 256` in this
   protocol. Do not substitute NPC object IDs or a zone index.
3. Keep packets have no separate response/request identifier. Bound concurrent
   requests and correlate replies before changing the selected page. A packet
   for another realm must not overwrite the current realm's data.
4. The six relic holders come from the server. Static atlas/JSON defaults do
   not prove current ownership. Distinguish missing information from unclaimed.
5. Battle/group records refer to zone quarters, not arbitrary world positions.
   The original battle service may be disabled. Missing battle packets must
   remain unknown rather than implying an empty battle map.
6. Teleport code 2 is a different gameplay action with original server rules.
   Do not expose it as part of the read-only window migration.
7. Reset cached ownership on logout/character changes. Scope the window's
   requests to a real playing session and rate-limit repeated Update clicks.

Acceptance order:

1. Bounded state/command contract and malformed/stale event tests.
2. Ordinary-player private-server requests for all three pages, retaining
   unchanged normal runtime and played database.
3. Reuse original atlases and window structure in a private native candidate.
4. Validate actual tab/Update/close behavior and original map markers; install
   only after the guarded predecessor checks pass.

The original siege-engine window is a separate contract (control/ammunition/
target actions). Record it for its own block instead of mixing it into this
information window.

Validated reference boundary: the pinned public DOL Keep table contains New
Frontiers rows in region 163. The existing window artwork contains classic
frontier tile zone IDs. Stable keep identities such as 50/75/100 can carry
ownership into the existing overview, as verified with three original DOL rows
in the disposable server. This does not establish a coordinate conversion
between classic frontiers and New Frontiers. Battle/player markers require an
exact tile-zone match; no inferred conversion, frontier scene replacement or
teleport action is part of this package. Relic-holder information uses the
original six-field server list separately from static relic-temple labels.
