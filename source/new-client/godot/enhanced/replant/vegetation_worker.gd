extends RefCounted
## Worker-only numeric generation. No SceneTree nodes, resources, rendering or physics calls.
var pixels:PackedByteArray
var heights:PackedFloat32Array
var hsize:int
var hcell:float
var water:PackedByteArray
var water_size:int
var levels:Dictionary
func _height(x:float,z:float) -> float:
	var gx=clampf(x/hcell,0,hsize-1.001);var gz=clampf(z/hcell,0,hsize-1.001);var ix=int(gx);var iz=int(gz);var fx=gx-ix;var fz=gz-iz
	var top=lerpf(heights[iz*hsize+ix],heights[iz*hsize+ix+1],fx);var bottom=lerpf(heights[(iz+1)*hsize+ix],heights[(iz+1)*hsize+ix+1],fx)
	return lerpf(top,bottom,fz)
func _water(x:float,z:float) -> float:
	if water_size==0:return -INF
	var ix=clampi(int(x/1638.4*water_size),0,water_size-1);var iz=clampi(int(z/1638.4*water_size),0,water_size-1)
	return float(levels.get(int(water[iz*water_size+ix]),-INF))
func _pick(r:float,urban:bool,rng:RandomNumberGenerator) -> String:
	if urban or r<.66:return "tapiz_bajo_%d"%rng.randi_range(0,1)
	if r<.78:return "hierba_fina_%d"%rng.randi_range(0,2)
	if r<.88:return "hierba_ancha_%d"%rng.randi_range(0,2)
	if r<.94:return "treboles_%d"%rng.randi_range(0,2)
	if r<.97:return "rosetas_%d"%rng.randi_range(0,2)
	if r<.98:return "helechos_%d"%rng.randi_range(0,1)
	if r<.989:return "hojas_largas_%d"%rng.randi_range(0,1)
	if r<.995:return "margaritas_%d"%rng.randi_range(0,2)
	return "flores_amarillas_%d"%rng.randi_range(0,2)
func generate(c:Vector2i) -> Dictionary:
	var start=Time.get_ticks_usec();var occupied=false
	for iz in range(c.y*10,mini(c.y*10+10,1024)):
		for ix in range(c.x*10,mini(c.x*10+10,1024)):
			if ix>=0 and iz>=0 and pixels[(iz*1024+ix)*4]>0:occupied=true;break
		if occupied:break
	if not occupied:return {"cell":c,"groups":{},"count":0,"generation_us":Time.get_ticks_usec()-start}
	var rng=RandomNumberGenerator.new();rng.seed=absi((c.x*73856093)^(c.y*19349663)^207241024);var groups={};var total=0
	for i in 10000:
		var point=Vector2((c.x+rng.randf())*16.0,(c.y+rng.randf())*16.0);var x=point.x;var z=point.y
		if x<0 or z<0 or x>=1638.4 or z>=1638.4:continue
		var ix=clampi(int(x/1.6),0,1023);var iz=clampi(int(z/1.6),0,1023);var off=(iz*1024+ix)*4
		var red=float(pixels[off])/255.0
		if red<=.001 or pixels[off+3]>25 or rng.randf()>red:continue
		var h=_height(x,z)
		if h<=_water(x,z)+.25:continue
		var species=_pick(rng.randf(),pixels[off+1]>127,rng);var scale=rng.randf_range(.7,1.25);var basis=Basis(Vector3.UP,rng.randf()*TAU)
		if species.begins_with("tapiz"):
			var dx=(_height(x+.2,z)-_height(x-.2,z))/.4;var dz=(_height(x,z+.2)-_height(x,z-.2))/.4
			basis=Basis(Quaternion(Vector3.UP,Vector3(-dx,1,-dz).normalized()))*basis
		basis=basis.scaled(Vector3.ONE*scale)
		var vigour=maxf(.65,float(pixels[off+2])/255.0);var rank=rng.randf()
		if not groups.has(species):groups[species]=[]
		var rows:Array=groups[species]
		rows.append_array([basis.x.x,basis.y.x,basis.z.x,x,basis.x.y,basis.y.y,basis.z.y,h-.005,basis.x.z,basis.y.z,basis.z.z,z,vigour,rank,0.0,1.0]);total+=1
	for name in groups:groups[name]=PackedFloat32Array(groups[name])
	return {"cell":c,"groups":groups,"count":total,"generation_us":Time.get_ticks_usec()-start}
