extends Node
## Local Inspector bridge. GO TO runs only after an explicit fresh request; no credentials are read.
const ROOT="res://.enhanced-session/godot_tools/Inspector/"
var viewer:Node
var elapsed:=0.0
var test_mode:=false
var output_path:=""
var last_count:=0
var last_request:=""
var pending_goto:Dictionary={}
func attach(scene:Node) -> void:
	viewer=scene
	scene.set_meta("enhanced_inspector_bridge",true)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(ROOT))
	if output_path.is_empty():output_path=ROOT+"snapshot.json"

func _process(delta:float) -> void:
	elapsed+=delta
	if elapsed<1.0:return
	elapsed=0
	if not is_instance_valid(viewer):return
	if not test_mode:
		if not FileAccess.file_exists(ROOT+"watch.json"):return
		var watch=JSON.parse_string(FileAccess.get_file_as_string(ROOT+"watch.json"))
		if not watch is Dictionary or absf(Time.get_unix_time_from_system()-float(watch.get("unix_time",0)))>8.0:return
	sample()
	if not test_mode:process_goto()

func goto_ack(id:String,state:String,message:String) -> void:
	var data={"request":id,"state":state,"message":message,"pid":OS.get_process_id(),"unix_time":Time.get_unix_time_from_system()}
	var file=FileAccess.open(ROOT+"goto_result.json.tmp",FileAccess.WRITE)
	if file!=null:
		file.store_string(JSON.stringify(data));file.close()
		DirAccess.rename_absolute(ProjectSettings.globalize_path(ROOT+"goto_result.json.tmp"),ProjectSettings.globalize_path(ROOT+"goto_result.json"))

func process_goto() -> void:
	var server=get_node_or_null("/root/Server")
	if server==null or not server.get("playing"):return
	if not pending_goto.is_empty():
		var player=viewer.get("player")
		var current=int(viewer.get("region").current.info.id)
		var now:Vector3=server.call("to_region",current,player.global_position)
		if int(server.entry.get("region",-1))==int(pending_goto.region) and now.distance_to(pending_goto.target)<160.0:
			goto_ack(pending_goto.id,"arrived","Posición confirmada por el cliente.");pending_goto={}
		elif Time.get_unix_time_from_system()>float(pending_goto.deadline):
			goto_ack(pending_goto.id,"error","El servidor no ha confirmado el salto. Comprueba los permisos GM.");pending_goto={}
	if not FileAccess.file_exists(ROOT+"goto_request.json"):return
	var request=JSON.parse_string(FileAccess.get_file_as_string(ROOT+"goto_request.json"))
	if not request is Dictionary:return
	var id=String(request.get("request",""))
	if id.is_empty() or id==last_request:return
	last_request=id
	if int(request.get("pid",-1))!=OS.get_process_id() or absf(Time.get_unix_time_from_system()-float(request.get("unix_time",0)))>10.0:return
	if String(request.get("project","")).replace("\\","/").trim_suffix("/").to_lower()!=ProjectSettings.globalize_path("res://").replace("\\","/").trim_suffix("/").to_lower():return
	var region=viewer.get("region");var player=viewer.get("player")
	var point:Vector3;var zid=int(region.current.info.id)
	if request.get("object_id","")!="":
		var snapshot=JSON.parse_string(FileAccess.get_file_as_string(output_path));var found=false
		for row in snapshot.get("objects",[]):
			if row.id!=request.object_id:continue
			point=Vector3(row.position[0],row.position[1],row.position[2]);found=true;break
		if not found:goto_ack(id,"error","El objeto ya no está en la captura actual.");return
		var toward:Vector3=player.global_position-point;toward.y=0.0
		if toward.length()>0.1:point+=toward.normalized()*5.0
		if not region.current.city:point.y=region.height_at(point.x,point.z,point.y)+0.4
	elif request.has("destination"):
		var destination=request.destination
		zid=int(destination.get("zone",-1))
		if not FileAccess.file_exists("res://content/zones/zone%03d/zone.json"%zid):goto_ack(id,"error","La zona de destino no está convertida en este cliente.");return
		var p=destination.get("position",[])
		if not p is Array or p.size()!=3:goto_ack(id,"error","Posición de destino no válida.");return
		point=Vector3(p[0],p[1],p[2])
	else:goto_ack(id,"error","Falta el objeto o destino de GO TO.");return
	if not point.is_finite():goto_ack(id,"error","Coordenadas no válidas.");return
	var target:Vector3=server.call("to_region",zid,point)
	var metadata:Dictionary=server.call("zone_info",zid)
	if metadata.is_empty():goto_ack(id,"error","No se reconoce la región del destino.");return
	server.call("command","/jump to %d %d %d %d"%[roundi(target.x),roundi(target.y),roundi(target.z),int(metadata.region)])
	pending_goto={"id":id,"target":target,"region":int(metadata.region),"deadline":Time.get_unix_time_from_system()+8.0}
	goto_ack(id,"sent","GO TO enviado al servidor; esperando confirmación.")

func in_view(camera:Camera3D,point:Vector3) -> bool:
	return camera!=null and camera.is_position_in_frustum(point)

func figure_images(npc:Node) -> Array:
	# Link only textures actually used by visible character parts, not every cached face/armour.
	var used:Dictionary={}
	for mesh in npc.find_children("*","MeshInstance3D",true,false):
		if not mesh.is_visible_in_tree() or mesh.mesh==null:continue
		for surface in mesh.mesh.get_surface_count():
			var material=mesh.get_active_material(surface)
			if material is ShaderMaterial:
				for parameter in ["albedo_tex","eye_tex","decal_tex","pattern_tex","logo_tex"]:
					var texture=material.get_shader_parameter(parameter)
					if texture is Texture2D:used[texture.get_instance_id()]=true
	var result:Array=[]
	for figure in npc.find_children("*","Node3D",true,false):
		var figure_script=figure.get_script()
		if figure_script==null or String(figure_script.resource_path)!="res://game/fig3_figure.gd":continue
		var dir=String(figure.get("_texture_dir"))
		var cache:Dictionary=figure_script._tex_cache
		for key in cache:
			var texture=cache[key]
			if not texture is Texture2D or not used.has(texture.get_instance_id()):continue
			if not String(key).begins_with(dir):continue
			var path=dir.path_join(String(key).trim_prefix(dir)+".png").replace("/x4plus/","/original/")
			var full=ProjectSettings.globalize_path(path)
			if FileAccess.file_exists(path) and not result.has(full):result.append(full)
	return result

func sample() -> Dictionary:
	var region=viewer.get("region")
	var player=viewer.get("player")
	if region==null or player==null or not is_instance_valid(region.current):return {}
	var camera=player.get("camera") as Camera3D
	if camera==null:camera=get_viewport().get_camera_3d()
	var origin:Vector3=player.global_position
	var objects:Array=[]
	var controllers:Dictionary={}
	for child in viewer.get_children():
		var script=child.get_script()
		if script!=null:controllers[String(script.resource_path).get_file()]=child
	for zone in region.zones.values():
		var zid=int(zone.info.id)
		for index in zone.info.fixtures.size():
			var fixture=zone.info.fixtures[index]
			var local=Vector3(fixture.pos[0],fixture.pos[1],fixture.pos[2])
			var position=zone.to_global(local)
			var distance=origin.distance_to(position)
			if distance>350.0:continue
			var model=zone.info.models[int(fixture.m)]
			var row={"id":"fixture:%d:%d"%[zid,index],"name":String(fixture.get("name",model.name)),"model":String(model.name),"kind":"Escenario","zone":zid,"model_file":zone.dir.path_join(String(model.file)),"distance_m":distance,"in_camera":in_view(camera,position+Vector3.UP*2),"position":[position.x,position.y,position.z]}
			var trees=controllers.get("elm_trial.gd")
			if trees!=null and trees.enabled and trees.bound_zone==zone and String(model.name).to_lower().begins_with("elm"):
				row["model_file"]="";row["kind"]="Árbol nuevo";row["note"]="Modelo de olmo preparado. Su imagen está incrustada; no se ofrece el atlas del árbol antiguo como si fuera el visible."
			var stone=controllers.get("stone_ivy_trial.gd")
			if stone!=null and stone.get("manifest") is Dictionary:
				for target in stone.manifest.get("targets",[]):
					if int(target.get("fixture",{}).get("id",-99999))!=int(fixture.get("id",-1)):continue
					if target.has("sculpt"):
						row["model_file"]="";row["kind"]="Roca nueva";row["note"]="Malla preparada de piedra. El material incrustado se conserva; no se ofrece la textura del monolito antiguo."
					else:row["note"]="Edificio con hiedra 3D aparte. La lista enlaza el modelo base; la hiedra preparada no se confunde con su capa antigua."
			objects.append(row)
		var here=zone.to_local(origin)
		if here.x>=0 and here.z>=0 and here.x<float(zone.info.size_m) and here.z<float(zone.info.size_m):
			var size=float(zone.info.size_m)/8.0
			var key="%d_%d"%[clampi(int(here.x/size),0,7),clampi(int(here.z/size),0,7)]
			var patch=zone.info.get("ground_splat",{}).get("patches",{}).get(key,{})
			var names:Array=[]
			for layer in patch.get("layers",[]):names.append(String(layer.tex))
			var row={"id":"terrain:%d:%s"%[zid,key],"name":"Suelo bajo tus pies · sector "+key,"model":"Capas reales del terreno","kind":"Suelo","zone":zid,"distance_m":0.0,"in_camera":true,"texture_names":names,"position":[origin.x,origin.y,origin.z]}
			var paths=controllers.get("paths_pbr.gd")
			if paths!=null and paths.mode>0 and paths.manifest.get("patches",[]).has(key):
				row["texture_names"].erase("h_soil");row["texture_names"].erase("h_tinypebbles")
				row["image_files"]=[]
				for spec in paths.manifest.maps:row.image_files.append(String(spec.path))
				row["note"]="Tierra y grava usan materiales nuevos de caminos: se enlazan sus mapas actuales, no los atlas que quedan ocultos."
			objects.append(row)
	var npcs=viewer.get("npcs")
	var review=controllers.get("elm_review_stand.gd")
	if review!=null and is_instance_valid(review.display) and review.display.visible:
		for item in review.rows:
			var row:Dictionary=item.duplicate(true)
			var p:=Vector3(row.position[0],row.position[1],row.position[2])
			if is_instance_valid(review.bound_zone):p=review.bound_zone.to_global(p)
			row["position"]=[p.x,p.y,p.z]
			if origin.distance_to(p)>350.0:continue
			row["distance_m"]=origin.distance_to(p)
			row["in_camera"]=in_view(camera,p+Vector3.UP*3)
			objects.append(row)
	if npcs!=null:
		for npc in npcs.active.values():
			if not is_instance_valid(npc):continue
			var position:Vector3=npc.global_position
			var distance=origin.distance_to(position)
			if distance>350.0:continue
			var row={"id":"npc:"+String(npc.spawn.get("id",npc.name)),"name":String(npc.spawn.get("name",npc.name)),"model":String(npc.info.get("name","")),"model_id":int(npc.spawn.get("model",0)),"skin_id":int(npc.spawn.get("skin",0)),"kind":"Personaje / mob","zone":int(region.current.info.id),"model_file":String(npc.info.get("gltf","")),"distance_m":distance,"in_camera":in_view(camera,position+Vector3.UP),"position":[position.x,position.y,position.z]}
			var images=figure_images(npc)
			if not images.is_empty():row["image_files"]=images;row["note"]="Partes visibles del personaje: sus texturas activas de cara, pelo y equipo se enlazan con sus originales."
			objects.append(row)
	var snapshot={"schema":1,"mode":"offline_test" if test_mode else "live","connected":true,"unix_time":Time.get_unix_time_from_system(),"pid":OS.get_process_id(),"project":ProjectSettings.globalize_path("res://"),"zone":int(region.current.info.id),"player_position":[origin.x,origin.y,origin.z],"camera_position":[camera.global_position.x,camera.global_position.y,camera.global_position.z] if camera!=null else [],"objects":objects}
	var server=get_node_or_null("/root/Server")
	snapshot["goto_supported"]=not test_mode and server!=null and bool(server.get("playing"))
	if server!=null:
		snapshot["character"]=String(server.selected.get("name","Sesión Godot"))
		snapshot["region"]=int(server.entry.get("region",0))
		var world:Vector3=server.call("to_region",int(region.current.info.id),origin)
		snapshot["player_world"]=[world.x,world.y,world.z]
	last_count=objects.size()
	var temp=output_path+".tmp"
	var file=FileAccess.open(temp,FileAccess.WRITE)
	if file!=null:
		file.store_string(JSON.stringify(snapshot));file.close()
		DirAccess.rename_absolute(ProjectSettings.globalize_path(temp),ProjectSettings.globalize_path(output_path))
	return snapshot

func _exit_tree() -> void:
	if output_path.is_empty() or not FileAccess.file_exists(output_path):return
	var value=JSON.parse_string(FileAccess.get_file_as_string(output_path))
	if not value is Dictionary or int(value.get("pid",-1))!=OS.get_process_id():return
	value["connected"]=false;value["unix_time"]=Time.get_unix_time_from_system()
	var file=FileAccess.open(output_path,FileAccess.WRITE)
	if file!=null:file.store_string(JSON.stringify(value))
