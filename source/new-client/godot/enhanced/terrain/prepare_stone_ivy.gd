extends SceneTree
const STATE:="res://.enhanced-session/stone_ivy/"
var data:Dictionary={}
var leaf_material:ShaderMaterial
var stem_material:StandardMaterial3D
var stone_material:ShaderMaterial

func _initialize() -> void:
	call_deferred("run")

func read_mesh(spec:Dictionary) -> ArrayMesh:
	assert(FileAccess.get_sha256(STATE+String(spec.vertex_file))==spec.vertex_sha256)
	assert(FileAccess.get_sha256(STATE+String(spec.index_file))==spec.index_sha256)
	var raw:=FileAccess.get_file_as_bytes(STATE+String(spec.vertex_file)).to_float32_array()
	var verts:=PackedVector3Array()
	var normals:=PackedVector3Array()
	var uv:=PackedVector2Array()
	var uv2:=PackedVector2Array()
	var colour:=PackedColorArray()
	assert(raw.size()==int(spec.vertices)*14)
	for i in int(spec.vertices):
		var k:=i*14
		verts.append(Vector3(raw[k],raw[k+1],raw[k+2]))
		normals.append(Vector3(raw[k+3],raw[k+4],raw[k+5]))
		uv.append(Vector2(raw[k+6],raw[k+7]))
		uv2.append(Vector2(raw[k+8],raw[k+9]))
		colour.append(Color(raw[k+10],raw[k+11],raw[k+12],raw[k+13]))
	var indices:=FileAccess.get_file_as_bytes(STATE+String(spec.index_file)).to_int32_array()
	assert(indices.size()==int(spec.triangles)*3)
	# Input is glTF-style CCW; ArrayMesh uses Godot's clockwise front faces.
	for i in int(indices.size()/3):
		var swap:=indices[i*3+1]
		indices[i*3+1]=indices[i*3+2]
		indices[i*3+2]=swap
	var arrays:=[]
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=verts
	arrays[Mesh.ARRAY_NORMAL]=normals
	arrays[Mesh.ARRAY_TEX_UV]=uv
	arrays[Mesh.ARRAY_TEX_UV2]=uv2
	arrays[Mesh.ARRAY_COLOR]=colour
	arrays[Mesh.ARRAY_INDEX]=indices
	var mesh:=ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	mesh.resource_name=String(spec.name)
	return mesh

func texture(path:String) -> ImageTexture:
	var image:=Image.load_from_file(path)
	assert(image!=null)
	image.generate_mipmaps()
	return ImageTexture.create_from_image(image)

func save_asset(entry:Dictionary) -> Dictionary:
	var root_node:=Node3D.new()
	root_node.name="Fixture_%d"%int(entry.fixture.id)
	for key in entry.meshes:
		var spec:Dictionary=entry.meshes[key]
		if int(spec.triangles)==0:continue
		var node:=MeshInstance3D.new()
		node.name=key
		node.mesh=read_mesh(spec)
		node.material_override=stone_material.duplicate() if key=="body" else (leaf_material if String(key).ends_with("leaves") else stem_material)
		root_node.add_child(node)
		node.owner=root_node
	var packed:=PackedScene.new()
	assert(packed.pack(root_node)==OK)
	var path:=STATE+"fixture_%d.scn"%int(entry.fixture.id)
	assert(ResourceSaver.save(packed,path,ResourceSaver.FLAG_COMPRESS)==OK)
	root_node.free()
	var result:Dictionary=entry.duplicate(true)
	result.scene=ProjectSettings.globalize_path(path)
	result.scene_sha256=FileAccess.get_sha256(path)
	return result

func run() -> void:
	data=JSON.parse_string(FileAccess.get_file_as_string(STATE+"geometry.json"))
	leaf_material=ShaderMaterial.new()
	leaf_material.shader=load("res://enhanced/terrain/ivy_leaf.gdshader")
	stem_material=StandardMaterial3D.new()
	stem_material.vertex_color_use_as_albedo=true
	stem_material.roughness=0.92
	stone_material=ShaderMaterial.new()
	stone_material.shader=load("res://enhanced/terrain/stone_surface.gdshader")
	var generated:Dictionary={}
	for map in data.maps:
		assert(FileAccess.get_sha256(String(map.path))==map.sha256)
		var param:String={"Diffuse":"stone_colour","nor_gl":"stone_normal","Rough":"stone_roughness"}[String(map.kind)]
		var tex:=texture(String(map.path))
		var texpath:=STATE+param+".res"
		assert(ResourceSaver.save(tex,texpath,ResourceSaver.FLAG_COMPRESS|ResourceSaver.FLAG_CHANGE_PATH)==OK)
		stone_material.set_shader_parameter(param,load(texpath))
		generated[ProjectSettings.globalize_path(texpath)]=FileAccess.get_sha256(texpath)
	var vine:=texture("res://content/zones/zone207/textures/x4plus/hclimbvine.png")
	var vinepath:=STATE+"original_ivy.res"
	assert(ResourceSaver.save(vine,vinepath,ResourceSaver.FLAG_COMPRESS|ResourceSaver.FLAG_CHANGE_PATH)==OK)
	stone_material.set_shader_parameter("original_ivy",load(vinepath))
	generated[ProjectSettings.globalize_path(vinepath)]=FileAccess.get_sha256(vinepath)
	var manifest:=data.duplicate(true)
	manifest.generated_resource_hashes=generated
	manifest.targets=[]
	for entry in data.targets:
		manifest.targets.append(save_asset(entry))
		print("STONE_IVY_SCENE_PREPARED fixture=",entry.fixture.id)
	var file:=FileAccess.open(STATE+"manifest.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest,"  "))
	print("STONE_IVY_PREPARE_OK scenes=",manifest.targets.size())
	quit()
