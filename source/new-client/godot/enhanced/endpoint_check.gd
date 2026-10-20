extends SceneTree
## Check endpoint argument parsing without opening a socket or using an account.
var expected := {}
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--expect-"):
			var pair := arg.trim_prefix("--expect-").split("=", true, 1)
			expected[pair[0]] = pair[1]
	run.call_deferred()
func run() -> void:
	var server := root.get_node("Server")
	var active: bool = server.get("active")
	var port: int = server.get("server_port")
	var has_client: bool = server.get("client") != null
	var ok: bool = port == int(expected.port) and active == (expected.active == "true") and has_client == (expected.client == "true")
	if expected.has("profile"):
		ok = ok and server.protocol_profile == expected.profile
		if has_client: ok = ok and server.client.ProtocolProfile == expected.profile
	if expected.get("error", "false") == "true":
		ok = ok and not String(server.get("last_error")).is_empty()
	print("ENDPOINT_ARGUMENT_CHECK ", JSON.stringify({"ok": ok, "port": port, "active": active, "client_created": has_client}))
	quit(0 if ok else 3)
