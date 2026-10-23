extends SceneTree
var args:Dictionary={}
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var pair:=arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
	call_deferred("run")
func run() -> void:
	Engine.max_fps=60;root.size=Vector2i(1280,900)
	var world:=Node3D.new();root.add_child(world)
	var zone=load("res://game/zone_loader.gd").new();world.add_child(zone)
	zone.load_zone("res://content/zones/zone207","blend","x4plus");zone.visible=false
	var floor_node:=MeshInstance3D.new();var plane:=PlaneMesh.new();plane.size=Vector2(100,100);floor_node.mesh=plane;world.add_child(floor_node)
	var ground:=StandardMaterial3D.new();ground.albedo_color=Color(0.14,0.22,0.09);ground.roughness=1;floor_node.material_override=ground
	var camera:=Camera3D.new();world.add_child(camera);camera.make_current();camera.fov=55;camera.far=1000
	var sky=load("res://game/sky_system.gd").new();world.add_child(sky);sky.setup(zone,camera,"x4plus");sky.set_hour(14);sky.time_scale=0;sky.set_process(false)
	DirAccess.make_dir_recursive_absolute(args.out)
	var measures:Array=[]
	for profile in ["reference","candidate"]:
		var manifest:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(args[profile]))
		assert(FileAccess.get_sha256(manifest.scene)==manifest.scene_sha256)
		var model:Node3D=load(String(manifest.scene)).instantiate();world.add_child(model)
		root.use_taa=true;root.msaa_3d=Viewport.MSAA_2X if profile=="reference" else Viewport.MSAA_4X
		var leaf:MeshInstance3D=model.find_children("Hojas_*","MeshInstance3D",true,false)[0]
		var arrays:Array=leaf.mesh.surface_get_arrays(0);var points:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX];var indices:PackedInt32Array=arrays[Mesh.ARRAY_INDEX]
		camera.position=Vector3(8,12,14);camera.look_at(Vector3(3,12,0))
		var targets:Array[Vector3]=[]
		for k in range(0,indices.size()-2,109*3):
			var a:Vector3=leaf.to_global(points[indices[k]]);var b:Vector3=leaf.to_global(points[indices[k+1]]);var c:Vector3=leaf.to_global(points[indices[k+2]])
			var center:Vector3=(a+b+c)/3.0
			if camera.is_position_behind(center):continue
			var pa:=camera.unproject_position(a);var pb:=camera.unproject_position(b);var pc:=camera.unproject_position(c)
			if absf((pb-pa).cross(pc-pa))*0.5>4.0:targets.append(center)
		var previous:Array=[];var deltas:Array[float]=[];var large:=0
		for step in 14:
			camera.position=Vector3(8+step*.025,12,14);camera.look_at(Vector3(3,12,0))
			for frame in (20 if step==0 else 4):await process_frame
			await RenderingServer.frame_post_draw
			var picture:=root.get_texture().get_image();var current:Array=[]
			if step in [0,13]:picture.save_png(String(args.out).path_join(profile+"_%02d.png"%step))
			for target in targets:
				var pixel:=camera.unproject_position(target);var x:=int(pixel.x);var y:=int(pixel.y)
				if x<2 or y<2 or x>=picture.get_width()-2 or y>=picture.get_height()-2:current.append(-1.0);continue
				var light:=0.0
				for dy in range(-1,2):
					for dx in range(-1,2):light+=picture.get_pixel(x+dx,y+dy).get_luminance()/9.0
				current.append(light)
			if not previous.is_empty():
				for i in current.size():
					if current[i]<0 or previous[i]<0:continue
					var difference:float=absf(current[i]-previous[i]);deltas.append(difference)
					if difference>.03:large+=1
			previous=current
		assert(not deltas.is_empty());deltas.sort();var total:=0.0
		for value in deltas:total+=value
		measures.append({"profile":profile,"scene_sha256":manifest.scene_sha256,"sample_pairs":deltas.size(),"jumps_over_0_03":large,"mean_luminance_delta":total/deltas.size(),"p95_delta":deltas[int(deltas.size()*.95)]})
		model.queue_free();await process_frame
	# A genuine mesh leaf with the same material, isolated for close-up material QA.
	for variant in ["oak","low"]:
		var bundle:String="res://.enhanced-session/forest_trial/bundles/detailed_"+String(variant)+"_20261023/forest.scn"
		var model:Node3D=load(bundle).instantiate();world.add_child(model)
		var leaves:MeshInstance3D=model.find_children("Hojas_*","MeshInstance3D",true,false)[0]
		var a:Array=leaves.mesh.surface_get_arrays(0);var count:=26 if variant=="oak" else 12
		var tiny:Array=[];tiny.resize(Mesh.ARRAY_MAX)
		for kind in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_COLOR]:tiny[kind]=a[kind].slice(0,count)
		var f:=PackedInt32Array()
		for i in range(0,a[Mesh.ARRAY_INDEX].size(),3):
			if a[Mesh.ARRAY_INDEX][i]>=count or a[Mesh.ARRAY_INDEX][i+1]>=count or a[Mesh.ARRAY_INDEX][i+2]>=count:break
			f.append_array(a[Mesh.ARRAY_INDEX].slice(i,i+3))
		tiny[Mesh.ARRAY_INDEX]=f
		var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,tiny);mesh.surface_set_material(0,leaves.mesh.surface_get_material(0))
		var specimen:=MeshInstance3D.new();specimen.mesh=mesh;world.add_child(specimen)
		var center:=mesh.get_aabb().get_center();var normal:Vector3=a[Mesh.ARRAY_NORMAL][0]
		model.visible=false;floor_node.visible=false
		camera.position=center+normal*0.65;camera.look_at(center,Vector3.UP if absf(normal.y)<.9 else Vector3.RIGHT)
		for frame in 30:await process_frame
		await RenderingServer.frame_post_draw;root.get_texture().get_image().save_png(String(args.out).path_join("detalle_"+variant+".png"))
		model.queue_free();specimen.queue_free();await process_frame
	var file:=FileAccess.open(String(args.out).path_join("leaf_motion_probe.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify({"measurements":measures,"note":"Isolated fixed-sun rendered probe; world-space leaf points tracked over 2.5cm camera steps. Not a claim of zero flicker in live gameplay."},"  "));file.close()
	print("FOREST_LEAF_PROBE_OK ",JSON.stringify(measures));quit()
