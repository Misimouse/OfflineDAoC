extends SceneTree
## Runs under the existing .NET Godot project, with no --server/account/password options.
## Connects its existing decoder ONLY to the isolated local packet fixture.
func _initialize() -> void: run.call_deferred()
func run() -> void:
	var port := 19727; var wire_port := 0; var report_path := ""; var duration := 22.0
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--port="): port=int(arg.trim_prefix("--port="))
		if arg.begins_with("--wire-port="): wire_port=int(arg.trim_prefix("--wire-port="))
		if arg.begins_with("--report="): report_path=arg.trim_prefix("--report=" )
		if arg.begins_with("--duration="): duration=float(arg.trim_prefix("--duration="))
	assert(wire_port>0)
	var folder: String = get_script().resource_path.get_base_dir()
	var bridge=load(folder.path_join("visual_bridge.gd")).new();root.add_child(bridge);assert(bridge.start(port)==OK)
	var client=load("res://game/net/DaocClient.cs").new();root.add_child(client)
	var adapter=load(folder.path_join("decoded_world_adapter.gd")).new();root.add_child(adapter)
	adapter.source_label="synthetic-wire-decoded-by-existing-DaocClient"
	adapter.bind_client(client,bridge,{"x":35,"y":51})
	assert(client.OpenAt("127.0.0.1",wire_port))
	print("BRIDGE_WIRE_READY")
	var began:=Time.get_ticks_msec()
	await create_timer(duration).timeout
	client.Close()
	var report={"synthetic":true,"existing_network_decoder":true,"events":adapter.events,
		"commands":bridge.commands,"connections":bridge.connections,"rejected":bridge.rejected,
		"graphics_loaded":false,"server_connected":false,"elapsed_ms":Time.get_ticks_msec()-began}
	var file:=FileAccess.open(report_path,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("BRIDGE_WIRE_FINISHED ",JSON.stringify(report));bridge.stop();quit()
