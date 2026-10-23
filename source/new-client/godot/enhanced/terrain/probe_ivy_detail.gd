extends SceneTree
var out:=""
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):out=arg.trim_prefix("--out=")
	call_deferred("run")
func run() -> void:
	root.size=Vector2i(900,900);root.msaa_3d=Viewport.MSAA_4X
	var scene:Node3D=load("res://.enhanced-session/stone_ivy/detail_20261023/fixture_1429.scn").instantiate()
	var sources:=scene.find_children("*leaves","MeshInstance3D",true,false);assert(sources.size()>0)
	var source:MeshInstance3D=sources[0];var old:Array=source.mesh.surface_get_arrays(0);var arrays:Array=[];arrays.resize(Mesh.ARRAY_MAX)
	for slot in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_TEX_UV2,Mesh.ARRAY_COLOR]:
		if old[slot]!=null:arrays[slot]=old[slot].slice(0,13)
	if old[Mesh.ARRAY_TANGENT]!=null:arrays[Mesh.ARRAY_TANGENT]=old[Mesh.ARRAY_TANGENT].slice(0,52)
	arrays[Mesh.ARRAY_INDEX]=old[Mesh.ARRAY_INDEX].slice(0,36)
	var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var world:=Node3D.new();root.add_child(world);var node:=MeshInstance3D.new();node.mesh=mesh;node.material_override=source.material_override;world.add_child(node)
	var center:=Vector3.ZERO
	for point in arrays[Mesh.ARRAY_VERTEX]:center+=point
	center/=13
	var normal:Vector3=arrays[Mesh.ARRAY_NORMAL][0].normalized();var radius:=0.0
	for point in arrays[Mesh.ARRAY_VERTEX]:radius=maxf(radius,point.distance_to(center))
	var camera:=Camera3D.new();world.add_child(camera);camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=radius*2.7;camera.position=center+normal*2;camera.look_at(center,Vector3.FORWARD if absf(normal.y)>.8 else Vector3.UP);camera.make_current()
	var environment:=WorldEnvironment.new();world.add_child(environment);environment.environment=Environment.new();environment.environment.background_mode=Environment.BG_COLOR;environment.environment.background_color=Color(.12,.15,.16);environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;environment.environment.ambient_light_color=Color.WHITE;environment.environment.ambient_light_energy=.85
	var sun:=DirectionalLight3D.new();world.add_child(sun);sun.position=center+normal*3;sun.look_at(center,Vector3.FORWARD if absf(normal.y)>.8 else Vector3.UP);sun.light_energy=.45
	for frame in 20:await process_frame
	await RenderingServer.frame_post_draw;root.get_texture().get_image().save_png(out.path_join("hoja_hiedra_cerca.png"));scene.free();print("IVY_DETAIL_PROBE_OK");quit()
