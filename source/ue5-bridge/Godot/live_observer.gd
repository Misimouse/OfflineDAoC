extends Node
## Optional READ-ONLY observer for an already running normal Godot scene.
## Does not disable graphics or replace player movement. Not installed automatically.
var transport: Node
var last_publish := 0
var supported_scene := false

func _ready() -> void:
	var folder: String = get_script().resource_path.get_base_dir()
	transport=load(folder.path_join("visual_bridge.gd")).new();add_child(transport)
	if transport.start()!=OK:
		push_error("Visual bridge port unavailable");queue_free()

func _process(_delta: float) -> void:
	if transport==null or Time.get_ticks_msec()-last_publish<50:return
	last_publish=Time.get_ticks_msec()
	var scene=get_tree().current_scene
	if scene==null:return
	# Do not assume a city, region transition or character screen has a zone viewer schema.
	var properties:Dictionary={}
	for prop in scene.get_property_list():properties[String(prop.name)]=true
	if not properties.has("zone") or not properties.has("player") or not properties.has("npcs"):
		if supported_scene:transport.publish([],207,"live-scene-observer");supported_scene=false
		return
	var zone=scene.get("zone");var player=scene.get("player");var world=scene.get("npcs")
	if not is_instance_valid(zone) or int(zone.info.get("id",-1))!=207 or not is_instance_valid(player):
		if supported_scene:transport.publish([],207,"live-scene-observer");supported_scene=false
		return
	supported_scene=true
	var p:Vector3=player.global_position;var yaw:float=player.facing()
	var rows:Array=[{"id":"player:local","kind":"player","name":"Local player","model_id":0,
		"position_m":[p.x,p.y,p.z],"forward_xz":[-sin(yaw),cos(yaw)],"state":"idle","health":1.0}]
	if is_instance_valid(world):
		var by_oid=world.get("by_oid")
		if by_oid is Dictionary:
			for oid in by_oid:
				var st=by_oid[oid]
				if st==null:continue
				var at:Vector3=st.pos
				if at.x<0 or at.z<0 or at.x>1638.4 or at.z>1638.4:continue
				rows.append({"id":"npc:"+str(oid),"kind":"npc","name":String(st.spawn.get("name","")),
					"model_id":int(st.spawn.get("model",0)),"position_m":[at.x,at.y,at.z],
					"forward_xz":[sin(st.yaw),cos(st.yaw)],"state":"dead" if not st.alive else "idle",
					"health":st.health})
				if rows.size()>=2048:break
	transport.publish(rows,207,"live-scene-observer")
