extends RefCounted
## Real mesh displacement. Subdivision is conforming within a surface; original edge/UV seams are pinned.
var error:=""
var report:Dictionary={}
func generate(original:Mesh,image:Image,rule:Dictionary) -> ArrayMesh:
	error="";report={}
	if original.get_surface_count()!=1:error="Selecciona una pieza de una superficie.";return null
	var src:=original.surface_get_arrays(0)
	for channel in [Mesh.ARRAY_CUSTOM0,Mesh.ARRAY_CUSTOM1,Mesh.ARRAY_CUSTOM2,Mesh.ARRAY_CUSTOM3]:
		if src[channel]!=null and src[channel].size()>0:error="Esta pieza usa canales especiales: se conserva sin cambios.";return null
	if src[Mesh.ARRAY_VERTEX]==null or src[Mesh.ARRAY_NORMAL]==null or src[Mesh.ARRAY_TEX_UV]==null:error="Esta pieza no tiene UV o normales utilizables.";return null
	var points:PackedVector3Array=src[Mesh.ARRAY_VERTEX]
	var normals:PackedVector3Array=src[Mesh.ARRAY_NORMAL]
	var uv:PackedVector2Array=src[Mesh.ARRAY_TEX_UV]
	if uv.size()!=points.size() or normals.size()!=points.size():error="Esta pieza no tiene UV o normales utilizables.";return null
	var vertices:Array=[];var faces:Array=[];var lookup:Dictionary={}
	var uv2:PackedVector2Array=src[Mesh.ARRAY_TEX_UV2] if src[Mesh.ARRAY_TEX_UV2]!=null else PackedVector2Array()
	var colours:PackedColorArray=src[Mesh.ARRAY_COLOR] if src[Mesh.ARRAY_COLOR]!=null else PackedColorArray()
	var indices:PackedInt32Array=src[Mesh.ARRAY_INDEX] if src[Mesh.ARRAY_INDEX]!=null else PackedInt32Array()
	if indices.is_empty():
		for i in points.size():indices.append(i)
	for i in range(0,indices.size(),3):
		var face:=[]
		for j in 3:
			var k:=indices[i+j]
			var key:=str([points[k].snapped(Vector3.ONE*0.00001),normals[k].snapped(Vector3.ONE*0.0001),uv[k].snapped(Vector2.ONE*0.00001)])
			if not lookup.has(key):
				lookup[key]=vertices.size()
				vertices.append({"p":points[k],"n":normals[k],"uv":uv[k],"uv2":uv2[k] if uv2.size()==points.size() else Vector2.ZERO,"c":colours[k] if colours.size()==points.size() else Color.WHITE,"pin":false})
			face.append(lookup[key])
		faces.append(face)
	var counts:Dictionary={}
	for f in faces:
		for j in 3:
			var edge:=Vector2i(mini(f[j],f[(j+1)%3]),maxi(f[j],f[(j+1)%3]))
			counts[edge]=int(counts.get(edge,0))+1
	for edge in counts:
		if counts[edge]!=2:vertices[edge.x].pin=true;vertices[edge.y].pin=true
	var spacing:=clampf(float(rule.get("spacing",0.25)),0.12,0.6)
	for iteration in 10:
		var mids:Dictionary={}
		for f in faces:
			for j in 3:
				var a:int=f[j];var b:int=f[(j+1)%3]
				var edge:=Vector2i(mini(a,b),maxi(a,b))
				if mids.has(edge) or vertices[a].p.distance_to(vertices[b].p)<=spacing:continue
				if vertices.size()>=60000:error="La pieza supera el presupuesto. Aumenta la separación de detalle.";return null
				var x:Dictionary=vertices[a];var y:Dictionary=vertices[b]
				mids[edge]=vertices.size()
				vertices.append({"p":(x.p+y.p)*0.5,"n":(x.n+y.n).normalized(),"uv":(x.uv+y.uv)*0.5,"uv2":(x.uv2+y.uv2)*0.5,"c":x.c.lerp(y.c,0.5),"pin":bool(x.pin) and bool(y.pin) and int(counts.get(edge,0))==1})
		if mids.is_empty():break
		var next:Array=[]
		for f in faces:
			var a:int=f[0];var b:int=f[1];var c:int=f[2]
			var ab:int=mids.get(Vector2i(mini(a,b),maxi(a,b)),-1)
			var bc:int=mids.get(Vector2i(mini(b,c),maxi(b,c)),-1)
			var ca:int=mids.get(Vector2i(mini(c,a),maxi(c,a)),-1)
			if ab>=0 and bc>=0 and ca>=0:next.append_array([[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]])
			elif ab>=0 and bc>=0:next.append_array([[a,ab,c],[ab,bc,c],[ab,b,bc]])
			elif bc>=0 and ca>=0:next.append_array([[b,bc,a],[bc,ca,a],[bc,c,ca]])
			elif ca>=0 and ab>=0:next.append_array([[c,ca,b],[ca,ab,b],[ca,a,ab]])
			elif ab>=0:next.append_array([[a,ab,c],[ab,b,c]])
			elif bc>=0:next.append_array([[b,bc,a],[bc,c,a]])
			elif ca>=0:next.append_array([[c,ca,b],[ca,a,b]])
			else:next.append(f)
		faces=next;counts.clear()
		for f in faces:
			for j in 3:
				var edge:=Vector2i(mini(f[j],f[(j+1)%3]),maxi(f[j],f[(j+1)%3]))
				counts[edge]=int(counts.get(edge,0))+1
	var adjacency:Array=[]
	for v in vertices:adjacency.append([])
	for edge in counts:adjacency[edge.x].append(edge.y);adjacency[edge.y].append(edge.x)
	var distances:=PackedInt32Array();distances.resize(vertices.size());distances.fill(99)
	var queue:Array=[]
	for i in vertices.size():
		if vertices[i].pin:distances[i]=0;queue.append(i)
	var cursor:=0
	while cursor<queue.size():
		var i:int=queue[cursor];cursor+=1
		if distances[i]>=2:continue
		for neighbour in adjacency[i]:
			if distances[neighbour]>distances[i]+1:distances[neighbour]=distances[i]+1;queue.append(neighbour)
	var out_points:=PackedVector3Array();var out_normals:=PackedVector3Array();var out_uv:=PackedVector2Array();var out_uv2:=PackedVector2Array();var out_colours:=PackedColorArray();var out_indices:=PackedInt32Array()
	var maximum:=0.0
	for i in vertices.size():
		var v:Dictionary=vertices[i]
		var sample:Vector2=Vector2(fposmod(v.uv.x,1.0),fposmod(v.uv.y,1.0))
		var pixel:=Vector2i(clampi(int(sample.x*image.get_width()),0,image.get_width()-1),clampi(int(sample.y*image.get_height()),0,image.get_height()-1))
		var colour:=image.get_pixelv(pixel)
		var height:float=(colour.r*0.2126+colour.g*0.7152+colour.b*0.0722)
		if bool(rule.get("invert",false)):height=1.0-height
		var mask:=1.0
		var regions:Array=rule.get("regions",[])
		if not regions.is_empty():
			mask=0.0
			for region in regions:
				var r:Array=region.rect
				if Rect2(r[0],r[1],r[2],r[3]).has_point(sample):
					mask=1.0 if region.category in ["Piedra","Madera","Tejado"] else 0.0
		var depth:=height*float(rule.get("depth_cm",2.0))*0.01*minf(1.0,float(distances[i])/2.0)*mask
		maximum=maxf(maximum,depth)
		out_points.append(v.p+v.n*depth);out_normals.append(Vector3.ZERO);out_uv.append(v.uv);out_uv2.append(v.uv2);out_colours.append(v.c)
	for f in faces:
		out_indices.append_array(f)
		var normal:Vector3=-(out_points[f[1]]-out_points[f[0]]).cross(out_points[f[2]]-out_points[f[0]])
		for i in f:out_normals[i]+=normal
	for i in out_normals.size():out_normals[i]=out_normals[i].normalized() if out_normals[i].length_squared()>0.000001 else vertices[i].n
	var arrays:=[];arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=out_points;arrays[Mesh.ARRAY_NORMAL]=out_normals;arrays[Mesh.ARRAY_TEX_UV]=out_uv
	if not uv2.is_empty():arrays[Mesh.ARRAY_TEX_UV2]=out_uv2
	if not colours.is_empty():arrays[Mesh.ARRAY_COLOR]=out_colours
	arrays[Mesh.ARRAY_INDEX]=out_indices
	var result:=ArrayMesh.new();result.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);result.surface_set_material(0,original.surface_get_material(0))
	report={"original_triangles":int(indices.size()/3),"triangles":faces.size(),"vertices":vertices.size(),"maximum_displacement_m":maximum,"source_mesh_unchanged":true,"real_geometry":true,"boundary_pinned":true}
	return result
