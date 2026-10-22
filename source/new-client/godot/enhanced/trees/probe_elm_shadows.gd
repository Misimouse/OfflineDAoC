extends "res://enhanced/trees/preview_elm_candidate.gd"
## Offline, paired shadow/no-shadow samples during a small camera move.
func run() -> void:
	await super.run()
	var sky
	for node in trial.get_parent().get_children():
		if node.get_script()!=null and String(node.get_script().resource_path).ends_with("sky_system.gd"):sky=node
	assert(sky!=null)
	var sun:DirectionalLight3D=sky.sun
	var results:Array=[]
	for configuration in [[2048,[0.1,0.2,0.5]],[4096,[0.06,0.15,0.4]]]:
		RenderingServer.directional_shadow_atlas_set_size(int(configuration[0]),true)
		sun.directional_shadow_split_1=configuration[1][0]
		sun.directional_shadow_split_2=configuration[1][1]
		sun.directional_shadow_split_3=configuration[1][2]
		var previous:=PackedFloat32Array()
		var deltas:Array[float]=[]
		var jumps:=0;var samples:=0
		for step in 18:
			cam.position=pivot+Vector3(4.0+step*0.025,3.0,12.0)
			cam.look_at(pivot+Vector3(0,0.1,2))
			var images:Array[Image]=[]
			for enabled in [true,false]:
				sun.shadow_enabled=enabled
				for frame in 3:await process_frame
				await RenderingServer.frame_post_draw
				images.append(root.get_texture().get_image())
			var current:=PackedFloat32Array()
			for y in range(int(images[0].get_height()*0.55),int(images[0].get_height()*0.9),8):
				for x in range(int(images[0].get_width()*0.1),int(images[0].get_width()*0.9),8):
					var shaded:=images[0].get_pixel(x,y).get_luminance()
					var plain:=images[1].get_pixel(x,y).get_luminance()
					current.append(shaded/maxf(plain,0.05))
			if not previous.is_empty():
				for i in current.size():
					var difference:=absf(current[i]-previous[i])
					deltas.append(difference);samples+=1
					if difference>0.12:jumps+=1
			previous=current
		deltas.sort()
		var total:=0.0
		for value in deltas:total+=value
		results.append({"atlas":configuration[0],"splits":configuration[1],"sample_pairs":samples,"jumps_over_0_12":jumps,"mean_shadow_ratio_delta":total/maxi(samples,1),"p95_delta":deltas[int(deltas.size()*.95)]})
	sun.shadow_enabled=true
	var file:=FileAccess.open(String(args.out).path_join("shadow_probe.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify({"scene_sha256":trial.manifest.scene_sha256,"measurements":results,"note":"Isolated rendered zone, fixed sunlight, 2.5cm camera steps. Ground shadow ratio only, no live gameplay; leaf-edge shimmer is a separate owner review."},"  "));file.close()
	print("ELM_SHADOW_PROBE_OK ",JSON.stringify(results))
	quit()
