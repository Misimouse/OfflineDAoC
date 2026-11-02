# Source snapshot validation â€” 2 November 2026

- All 237 Python tool/test source files parsed successfully after path generalization.
- `python -m unittest -v test_protocol.py`: 6 tests passed.
- Portable Godot transport check: 21 checks passed; `live_gateway.gd` and `visual_bridge.gd` parse checks passed.
- Portable launcher: .NET 10 Release build succeeded with zero warnings and zero errors, using the locally supplied SDK and no package feed.
- Runtime C++/header/build-rule source matches the previously compiled and accepted local plugin after normalization of line endings and whitespace-only blank lines. No native gameplay behavior was changed for repository export.
- Publication inventory excludes runtime reports, played databases, credentials, backups, imported/converted assets, generated catalogues, binaries and local Android File Server tokens. Personal workstation paths and character labels were removed from the source copy.

The source export has portable environment paths and a new README. Historical diagnostic/finalizer snippets retain generic example paths and require local review. Native content-dependent suites and live QA are not rerun by source publication; their prior local validation is described in README.md. A source checkout without regenerated private assets is not a playable distribution.


## Functional client update, 2026-11-03

Inventory and independent preview corrections were published as `0ab42cb`. The next local installed block passed 313 general native checks, 128 modular armour checks, 27 Godot interaction checks and an isolated original-server test covering equip/unequip, purchase, sale and item/horse-ticket icons. A read-only replay of that disposable merchant snapshot was rendered and visually inspected: the original shop window and icons remain visible after character UI initialization. These tests do not certify every class, every item, complete character creation, all armour attachments or performance in Connacht. The new optional library contains nine figures, 251 material sections and 661 available armour textures. Private reports, snapshots and assets remain excluded.
