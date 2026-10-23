extends Node3D
## Seat a broad-tree root collar on the terrain, preserving its shape and physics.
func _ready() -> void:
	var zone:Node=get_parent()
	while zone!=null and not zone.has_method("height_at"):zone=zone.get_parent()
	if zone==null:return
	for stem in find_children("Broad_root_*","Node3D",true,false):
		var at:Vector3=zone.to_local(stem.global_position)
		at.y=zone.height_at(at.x,at.z)-0.045
		stem.global_position=zone.to_global(at)
