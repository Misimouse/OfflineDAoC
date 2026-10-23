extends RefCounted
## Separate SHADOWS_ONLY foliage envelopes: never change visible leaves or depth prepass.
## ArrayMesh.shadow_mesh is deliberately not used: its positions must match the visible mesh.
static func add_proxy(leaf:MeshInstance3D,vertices_per_cluster:int) -> int:
	var arrays:Array=leaf.mesh.surface_get_arrays(0)
	var source:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
	assert(vertices_per_cluster>0 and source.size()%vertices_per_cluster==0)
	var vertices:=PackedVector3Array();var faces:=PackedInt32Array()
	for start in range(0,source.size(),vertices_per_cluster):
		var bounds:=AABB(source[start],Vector3.ZERO)
		for i in range(start,start+vertices_per_cluster):bounds=bounds.expand(source[i])
		var center:Vector3=bounds.get_center()
		var extent:Vector3=bounds.size*0.36
		extent=extent.max(Vector3.ONE*0.025)
		var base:=vertices.size()
		# Low polygon convex envelope for one attached leafy shoot group.
		for lat in range(1,4):
			var elevation:=PI*float(lat)/4.0
			for lon in 8:
				var azimuth:=TAU*float(lon)/8.0
				vertices.append(center+extent*Vector3(sin(elevation)*cos(azimuth),sin(elevation)*sin(azimuth),cos(elevation)))
		vertices.append(center+Vector3(0,0,extent.z));vertices.append(center-Vector3(0,0,extent.z))
		for lon in 8:
			var next:=(lon+1)%8
			faces.append_array(PackedInt32Array([base+24,base+next,base+lon,base+25,base+16+lon,base+16+next]))
			for lat in 2:
				var a:=base+lat*8+lon;var b:=base+lat*8+next
				faces.append_array(PackedInt32Array([a,b,a+8,b,b+8,a+8]))
	var data:Array=[];data.resize(Mesh.ARRAY_MAX);data[Mesh.ARRAY_VERTEX]=vertices;data[Mesh.ARRAY_INDEX]=faces
	var shadow:=ArrayMesh.new();shadow.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,data)
	var proxy:=MeshInstance3D.new();proxy.name="CopaShadow";proxy.mesh=shadow;proxy.transform=leaf.transform
	proxy.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
	leaf.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	leaf.get_parent().add_child(proxy)
	return faces.size()/3
