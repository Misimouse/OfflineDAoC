# Source snapshot validation â€” 2 November 2026

- All 237 Python tool/test source files parsed successfully after path generalization.
- `python -m unittest -v test_protocol.py`: 6 tests passed.
- Portable Godot transport check: 21 checks passed; `live_gateway.gd` and `visual_bridge.gd` parse checks passed.
- Portable launcher: .NET 10 Release build succeeded with zero warnings and zero errors, using the locally supplied SDK and no package feed.
- Runtime C++/header/build-rule source matches the previously compiled and accepted local plugin after normalization of line endings and whitespace-only blank lines. No native gameplay behavior was changed for repository export.
- Publication inventory excludes runtime reports, played databases, credentials, backups, imported/converted assets, generated catalogues, binaries and local Android File Server tokens. Personal workstation paths and character labels were removed from the source copy.

The source export has portable environment paths and a new README. Historical diagnostic/finalizer snippets retain generic example paths and require local review. Native content-dependent suites and live QA are not rerun by source publication; their prior local validation is described in README.md. A source checkout without regenerated private assets is not a playable distribution.
