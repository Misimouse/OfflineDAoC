extends SceneTree
var args:Dictionary={}
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var pair:=arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
	call_deferred("run")
func lathe(profile:Array,kind:String,material:Material) -> MeshInstance3D:
	var p:=PackedVector3Array();var uv:=PackedVector2Array();var indices:=PackedInt32Array();var sides:=192
	for ring in profile.size():
		var r:float=profile[ring].x;var h:float=profile[ring].y
		for j in sides+1:
			var a:float=TAU*j/sides;var radius:float=r*(1+.019*sin(a*5+.3)+.012*sin(a*9))
			var y:float=h
			if kind=="gills":y-=.035*(.5+.5*cos(a*96))*sin(PI*clampf((r-.21)/1.25,0,1))
			elif kind=="cap":y+=.025*sin(a*4+r*3)*r
			p.append(Vector3(cos(a)*radius+.06*h*h,y,sin(a)*radius))
			uv.append(Vector2(.5+cos(a)*r*.33,.5+sin(a)*r*.33) if kind=="cap" else Vector2(float(j)/sides*3,h*.65))
			if ring>0 and j<sides:
				var b:int=ring*(sides+1)+j;var c:int=b-sides-1
				indices.append_array(PackedInt32Array([c,b,c+1,c+1,b,b+1]))
	var arrays:Array=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=p;arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_INDEX]=indices
	var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	if kind!="stem":
		for i in range(0,indices.size(),3):
			var swap:int=indices[i];indices[i]=indices[i+2];indices[i+2]=swap
		arrays[Mesh.ARRAY_INDEX]=indices;mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var tool:=SurfaceTool.new();tool.create_from(mesh,0);tool.generate_normals();mesh=tool.commit();mesh.surface_set_material(0,material)
	var instance:=MeshInstance3D.new();instance.name=kind;instance.mesh=mesh;return instance
func run() -> void:
	var image:=Image.load_from_file(args.texture);assert(image!=null);image.generate_mipmaps()
	var cap:=StandardMaterial3D.new();cap.albedo_texture=ImageTexture.create_from_image(image);cap.albedo_color=Color(.78,.72,.79);cap.roughness=1;cap.metallic_specular=0;cap.cull_mode=BaseMaterial3D.CULL_DISABLED;cap.texture_filter=BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	var stem_image:=Image.load_from_file(args.stem);assert(stem_image!=null);stem_image.generate_mipmaps()
	var stem:=StandardMaterial3D.new();stem.albedo_texture=ImageTexture.create_from_image(stem_image);stem.albedo_color=Color(.8,.70,.62);stem.roughness=1;stem.metallic_specular=0;stem.cull_mode=BaseMaterial3D.CULL_DISABLED;stem.texture_filter=BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	var gills:=stem.duplicate();gills.albedo_color=Color(.65,.46,.52)
	var scene:=Node3D.new();scene.name="Seta_magica_redondeada"
	var profile:Array=[]
	for j in 33:
		var t:float=float(j)/32;profile.append(Vector2(.24*(1+.32*exp(-t*12)-.15*sin(t*PI)), -.18+t*1.98))
	scene.add_child(lathe(profile,"stem",stem));profile=[]
	for j in 41:
		var t:float=float(j)/40;profile.append(Vector2(maxf(.001,1.46*sin(t*PI/2)),2.65-.85*(1-cos(t*PI/2))))
	scene.add_child(lathe(profile,"cap",cap));profile=[]
	for j in 33:
		var t:float=float(j)/32;profile.append(Vector2(1.46*(1-t)+.21*t,1.80-.12*sin(t*PI)-.04*t))
	scene.add_child(lathe(profile,"gills",gills))
	for child in scene.get_children():child.owner=scene
	var packed:=PackedScene.new();assert(packed.pack(scene)==OK);DirAccess.make_dir_recursive_absolute(args.out)
	var path:=String(args.out).path_join("mushroom.scn");assert(ResourceSaver.save(packed,path,ResourceSaver.FLAG_COMPRESS)==OK)
	var file:=FileAccess.open(String(args.out).path_join("manifest.json"),FileAccess.WRITE);file.store_string(JSON.stringify({"scene":path,"sha256":FileAccess.get_sha256(path),"texture":args.texture,"texture_sha256":FileAccess.get_sha256(args.texture),"stem_texture":args.stem,"stem_texture_sha256":FileAccess.get_sha256(args.stem),"giant_scale":3.5,"giant_x":1310,"giant_z":1248,"cap_diameter_metres":10.22,"rim_headroom_metres":6.3},"  "));file.close()
	scene.free();print("MUSHROOM_PREPARED");quit()
