extends SceneTree
var bridge: Node
var began := 0
var frames := 0
var target := ""
var report_path := ""
var duration := 45.0

func _initialize() -> void: run.call_deferred()
func run() -> void:
	var port := 19727
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--port="): port = int(arg.trim_prefix("--port="))
		if arg.begins_with("--report="): report_path = arg.trim_prefix("--report=")
		if arg.begins_with("--duration="): duration = float(arg.trim_prefix("--duration="))
	bridge = load("res://visual_bridge.gd").new(); root.add_child(bridge)
	assert(bridge.start(port) == OK)
	bridge.command_received.connect(func(command: Dictionary):
		if command.action == "select_preview": target = String(command.get("entity_id", "")))
	began = Time.get_ticks_msec()
	print("BRIDGE_PROOF_READY port=",port)
	while float(Time.get_ticks_msec()-began)/1000.0 < duration:
		var elapsed := float(Time.get_ticks_msec()-began)/1000.0
		var entities: Array = []
		for i in 4:
			# Explicit synthetic test entities: not NPCs from a server or save.
			if i == 3 and fmod(elapsed,8.0) >= 4.0: continue
			entities.append({"id":"proof:%d"%i, "kind":"player" if i == 0 else "npc",
				"name":"Synthetic bridge proof %d"%i, "model_id":0,
				"position_m":[1304.0 + i*2.0 + sin(elapsed)*1.5,132.0,1245.0 + cos(elapsed)*1.5],
				"forward_xz":[cos(elapsed),sin(elapsed)], "state":"walk", "health":1.0})
		assert(bridge.publish(entities,207,"synthetic-proof")); frames += 1
		await create_timer(0.05).timeout
	var report := {"synthetic":true, "frames":frames, "connections":bridge.connections,
		"commands":bridge.commands, "rejected":bridge.rejected, "selected_preview":target,
		"elapsed_ms":Time.get_ticks_msec()-began, "graphics_loaded":false, "server_connected":false}
	if not report_path.is_empty():
		var file := FileAccess.open(report_path,FileAccess.WRITE); file.store_string(JSON.stringify(report,"  ")); file.close()
	print("BRIDGE_PROOF_FINISHED ",JSON.stringify(report)); bridge.stop(); quit()
