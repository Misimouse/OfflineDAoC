# Isolated Godot client checks

The normal client accepts `--server-port=10310` in its user arguments, alongside the existing `--server=127.0.0.1`. Omitting the port retains 10300. Malformed and out-of-range ports disable connection before creating a client. C# `Open(host)` remains compatible; `OpenAt(host, port)` selects a development endpoint using the same protocol.

Build `source/new-client/godot/MMOEngine.csproj` with .NET 10 and the matching Godot 4.7.2 Mono SDK packages. Keep the SDK, NuGet cache, converted art and build outputs outside Git. Do not deploy over a running playable installation. Obtain authorization before starting even a copied server, as required by AGENTS.md.

The following development scripts run with the matching Godot Mono engine, `--path PROJECT --script res://enhanced/SCRIPT.gd -- ...`:

- `endpoint_check.gd`: parser checks with no network connection; use `--expect-port=PORT`, `--expect-active=true|false`, `--expect-client=true|false` and the endpoint arguments being tested. Invalid cases also use `--expect-error=true`.
- `compatibility_probe.gd`: protocol login, character list/creation, world entry, NPC/trainer interaction and a small movement. Requires a deliberately disposable account on a server copy.
- `gameplay_check.gd`: the normal Server autoload, zone scene, player and NPC rendering, fixed-light A/B captures and graceful logout. Requires an existing disposable Hibernian character in zone207 and matching converted art.

Both integration scripts read `--probe-config=ABSOLUTE_PRIVATE_JSON`. They reject endpoints other than loopback and reject the normal 10300 port. Do not use real account credentials or put the JSON in Git. The baseline configuration has `host`, integer `port`, `account`, `password`, `report` (protocol output file), and `output` (gameplay output directory). See the scripts for optional creation/interaction fields; a new server fork may require different creation rules. Passwords belong only in the private file, never in a process argument or report.

Make a consistent SQLite backup with the source opened read-only before making an isolated copy. Bind the copied server to loopback on unused TCP/region ports; change only its own region endpoints and test data. Keep a hash manifest and the untouched snapshot separately from the disposable played copy. Disable copied autonomous population only for the controlled graphics baseline, without changing the original server's population or rules.

The local 20 October baseline used the OfflineDAoC v0.37c server and its copied DB, not the separate DOLSharp Lab database. Login, world entry, 142 protocol NPCs, a Caoimhe trainer reply and persisted movement passed. A rendered normal Ardee scene also passed. This establishes the test harness; it does not prove compatibility with the Lab fork or authorize a database migration. That requires an independent snapshot/export and the same checks against a separately bound Lab runtime.
