extends Node
## Attach the resource adapter to any normal Godot game session, independently of the LAB launcher.
var elapsed:=0.0
func _process(delta:float) -> void:
	elapsed+=delta
	if elapsed<1.0:return
	elapsed=0.0
	var scene=get_tree().current_scene
	if scene==null or scene.get_meta("enhanced_inspector_bridge",false):return
	var script=scene.get_script()
	if script==null or String(script.resource_path)!="res://game/zone_viewer.gd":return
	var region=scene.get("region");var player=scene.get("player")
	if region==null or player==null or not is_instance_valid(region.current):return
	var bridge=load("res://enhanced/godot_tools/inspector_bridge.gd").new()
	scene.add_child(bridge);bridge.attach(scene)
