extends SceneTree
const Relief=preload("res://enhanced/building_studio/relief_mesh.gd")
func _initialize() -> void:
	var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=PackedVector3Array([Vector3(-1,0,-1),Vector3(1,0,-1),Vector3(1,0,1),Vector3(-1,0,1)])
	arrays[Mesh.ARRAY_NORMAL]=PackedVector3Array([Vector3.UP,Vector3.UP,Vector3.UP,Vector3.UP])
	arrays[Mesh.ARRAY_TEX_UV]=PackedVector2Array([Vector2(0,0),Vector2(1,0),Vector2(1,1),Vector2(0,1)])
	arrays[Mesh.ARRAY_TEX_UV2]=arrays[Mesh.ARRAY_TEX_UV].duplicate()
	arrays[Mesh.ARRAY_COLOR]=PackedColorArray([Color.RED,Color.RED,Color.RED,Color.RED])
	arrays[Mesh.ARRAY_INDEX]=PackedInt32Array([0,1,2,0,2,3])
	var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var image=Image.create(8,8,false,Image.FORMAT_RGBA8);image.fill(Color.WHITE)
	var generator=Relief.new()
	var output=generator.generate(mesh,image,{"spacing":0.2,"depth_cm":4,"regions":[{"rect":[0.0,0.0,0.5,1.0],"category":"Piedra"},{"rect":[0.5,0.0,0.5,1.0],"category":"Ventana"}]})
	var checks={"generated":output!=null,"source_vertices_unchanged":mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]==arrays[Mesh.ARRAY_VERTEX]}
	if output!=null:
		var out=output.surface_get_arrays(0);var moved=false;var protected=true;var borders=true;var normal_ok=true
		for i in out[Mesh.ARRAY_VERTEX].size():
			var p:Vector3=out[Mesh.ARRAY_VERTEX][i];var uv:Vector2=out[Mesh.ARRAY_TEX_UV][i]
			moved=moved or p.y>0.001
			if uv.x>=0.5 and uv.x<0.99:protected=protected and absf(p.y)<0.00001
			if absf(p.x)>0.999 or absf(p.z)>0.999:borders=borders and absf(p.y)<0.00001
			normal_ok=normal_ok and out[Mesh.ARRAY_NORMAL][i].y>0.9
		checks.merge({"actual_vertices_moved":moved,"window_region_protected":protected,"boundaries_pinned":borders,"normals_face_out":normal_ok,"uv2_preserved":out[Mesh.ARRAY_TEX_UV2].size()==out[Mesh.ARRAY_VERTEX].size(),"colors_preserved":out[Mesh.ARRAY_COLOR].size()==out[Mesh.ARRAY_VERTEX].size()})
	var bad=ArrayMesh.new();var no_uv=arrays.duplicate();no_uv[Mesh.ARRAY_TEX_UV]=null;bad.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,no_uv)
	checks["unsupported_mesh_rejected"]=generator.generate(bad,image,{})==null
	print("GEOMETRY_CHECKS ",JSON.stringify(checks))
	var passed=true
	for value in checks.values():passed=passed and value
	quit(0 if passed else 1)
