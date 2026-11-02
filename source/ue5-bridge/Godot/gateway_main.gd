extends SceneTree
func _initialize()->void:run.call_deferred()
func run()->void:
	var folder:String=get_script().resource_path.get_base_dir()
	var gateway=load(folder.path_join("live_gateway.gd")).new();root.add_child(gateway)
