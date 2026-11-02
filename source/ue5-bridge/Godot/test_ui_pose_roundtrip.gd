extends SceneTree
func _initialize()->void:run.call_deferred()
func run()->void:
    var pose=load(get_script().resource_path.get_base_dir().path_join("ui_player_pose.gd")).new();root.add_child(pose);var server=root.get_node("Server");var failures:Array=[];var count:=0
    for heading in [0,1,511,1024,1536,2048,2560,3072,3584,4095]:
        count+=1;pose.heading=heading
        if server.heading_of(fposmod(-rad_to_deg(pose.facing()),360.0))!=heading:failures.append(heading)
    var report:={"passed":failures.is_empty(),"checks":count,"failures":failures,"uses_original_server_heading_conversion":true};var f:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/spell_casting/heading_tests.json"),FileAccess.WRITE);f.store_string(JSON.stringify(report));f.close();print(JSON.stringify(report));quit(0 if failures.is_empty() else 1)
