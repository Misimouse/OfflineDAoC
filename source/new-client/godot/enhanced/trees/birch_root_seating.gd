extends Node3D
## Seat each stem of a grove on its own terrain sample, without changing physics.
func _ready() -> void:
	var zone:Node=get_parent()
	while zone!=null and not zone.has_method("height_at"):zone=zone.get_parent()
	if zone==null:return
	for stem in find_children("Birch_root_*","Node3D",true,false):
		var at:Vector3=zone.to_local(stem.global_position)
		at.y=zone.height_at(at.x,at.z)-0.045
		stem.global_position=zone.to_global(at)
