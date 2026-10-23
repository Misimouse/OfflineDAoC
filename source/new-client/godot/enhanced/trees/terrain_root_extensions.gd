extends RefCounted
## Continue the actual trunk cross-section below downhill soil, without moving the crown.
var contours:Dictionary={}
var report:Dictionary={"skirts":0,"lower_vertices":0,"maximum_depth":0.0,"exposed_lower_vertices":0}
func apply(asset:Node3D,zone:Node3D) -> Array:
	var added:Array=[]
	for node in asset.find_children("*","MeshInstance3D",true,false):
		var label:=String(node.name).to_lower()
		if not (label.begins_with("tronco") or label.begins_with("wood")):continue
		if label.contains("brotes"):continue
		var stem:Node3D=asset
		var parent:Node=node.get_parent()
		while parent!=asset:
			if String(parent.name).to_lower().contains("root_"):stem=parent;break
			parent=parent.get_parent()
		var scale_y:float=node.global_transform.basis.get_scale().x
		var plane_y:float=stem.global_position.y+.16*scale_y
		var inverse:Transform3D=node.global_transform.affine_inverse()
		var normal:Vector3=node.global_transform.basis.transposed()*Vector3.UP
		var offset:float=plane_y-node.global_position.y
		var key:String="%d:%s:%.3f"%[node.mesh.get_instance_id(),str((normal/scale_y).snapped(Vector3.ONE*.001)),offset/scale_y]
		if not contours.has(key):contours[key]=slice_mesh(node.mesh,normal/scale_y,offset/scale_y)
		var mesh:=ArrayMesh.new()
		for surface in contours[key]:
			var vertices:=PackedVector3Array();var normals:=PackedVector3Array();var uv:=PackedVector2Array();var indices:=PackedInt32Array()
			for segment in surface.edges:
				var start:int=vertices.size()
				for endpoint in 2:
					var point:Vector3=segment[endpoint].p
					var world:Vector3=node.to_global(point);var local:Vector3=zone.to_local(world)
					var soil:float=zone.height_at(local.x,local.z)
					var bottom:Vector3=world;bottom.y=minf(world.y-.12,zone.to_global(Vector3(local.x,soil-.22,local.z)).y)
					vertices.append(point);vertices.append(inverse*bottom)
					normals.append(segment[endpoint].n);normals.append(segment[endpoint].n)
					uv.append(segment[endpoint].uv);uv.append(segment[endpoint].uv+segment[endpoint].uv_height*((inverse*bottom-point).dot(normal.normalized())))
					report.lower_vertices+=1;report.maximum_depth=maxf(report.maximum_depth,world.distance_to(bottom))
					if zone.to_local(bottom).y>soil-.15:report.exposed_lower_vertices+=1
				indices.append_array(PackedInt32Array([start,start+1,start+2,start+2,start+1,start+3]))
			if vertices.is_empty():continue
			var arrays:Array=[];arrays.resize(Mesh.ARRAY_MAX)
			arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_NORMAL]=normals;arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_INDEX]=indices
			var intermediate:=ArrayMesh.new();intermediate.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
			var tool:=SurfaceTool.new();tool.create_from(intermediate,0);tool.generate_tangents()
			var with_tangents:=tool.commit()
			mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,with_tangents.surface_get_arrays(0));mesh.surface_set_material(mesh.get_surface_count()-1,surface.material)
		if mesh.get_surface_count()==0:continue
		var skirt:=MeshInstance3D.new();skirt.name="Continuacion_enterrada";skirt.mesh=mesh
		node.add_child(skirt);added.append(skirt);report.skirts+=1
	return added
func slice_mesh(mesh:Mesh,normal:Vector3,offset:float) -> Array:
	var result:Array=[]
	for s in mesh.get_surface_count():
		var a:Array=mesh.surface_get_arrays(s);var p:PackedVector3Array=a[Mesh.ARRAY_VERTEX];var f:PackedInt32Array=a[Mesh.ARRAY_INDEX]
		var distances:=PackedFloat32Array();distances.resize(p.size())
		for i in p.size():distances[i]=p[i].dot(normal)-offset
		var edges:Array=[]
		for triangle in range(0,f.size(),3):
			if (distances[f[triangle]]<0)==(distances[f[triangle+1]]<0) and (distances[f[triangle]]<0)==(distances[f[triangle+2]]<0):continue
			var points:Array=[]
			var e1:Vector3=p[f[triangle+1]]-p[f[triangle]];var e2:Vector3=p[f[triangle+2]]-p[f[triangle]]
			var aa:float=e1.dot(e1);var bb:float=e1.dot(e2);var cc:float=e2.dot(e2);var determinant:float=aa*cc-bb*bb
			var uv_height:=Vector2.ZERO
			if absf(determinant)>1e-12:
				var d:=normal.normalized();var u1:Vector2=a[Mesh.ARRAY_TEX_UV][f[triangle+1]]-a[Mesh.ARRAY_TEX_UV][f[triangle]];var u2:Vector2=a[Mesh.ARRAY_TEX_UV][f[triangle+2]]-a[Mesh.ARRAY_TEX_UV][f[triangle]]
				uv_height=u1*((cc*e1.dot(d)-bb*e2.dot(d))/determinant)+u2*((aa*e2.dot(d)-bb*e1.dot(d))/determinant)
			for edge in 3:
				var i:int=f[triangle+edge];var j:int=f[triangle+(edge+1)%3]
				var da:float=distances[i];var db:float=distances[j]
				if (da<0)==(db<0):continue
				var t:float=da/(da-db)
				points.append({"p":p[i].lerp(p[j],t),"n":a[Mesh.ARRAY_NORMAL][i].lerp(a[Mesh.ARRAY_NORMAL][j],t).normalized(),"uv":a[Mesh.ARRAY_TEX_UV][i].lerp(a[Mesh.ARRAY_TEX_UV][j],t),"uv_height":uv_height})
			if points.size()==2:edges.append(points)
		result.append({"edges":edges,"material":mesh.surface_get_material(s)})
	return result
