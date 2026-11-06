extends SceneTree
var checks:=0
func check(value:bool,label:String)->void:
    checks+=1
    if not value:push_error(label);quit(1);assert(false,label)
func _initialize()->void:
    var flags=load(get_script().resource_path.get_base_dir().path_join("movement_flags_state.gd")).new()
    check(flags.consume({}) and flags.on_ground and flags.state(false)==0,"legacy ground movement retained")
    check(flags.consume({"swimming":true,"on_ground":false,"vertical_speed_mps":-1.5}),"native swimming facts accepted")
    check(flags.swimming and not flags.on_ground and flags.state(false)==4 and flags.vertical_speed_mps==-1.5,"original swimming state and signed vertical velocity retained")
    check(flags.state(true)==16,"sitting cannot forge the combined death state")
    check(flags.consume({"swimming":true,"on_ground":true}) and not flags.on_ground,"swimmer is never marked grounded")
    for invalid in [NAN,INF,"2",null,101,-101]:
        check(not flags.consume({"vertical_speed_mps":invalid}),"invalid vertical velocity rejected")
    for key in ["swimming","on_ground"]:
        for invalid in [0,1,"true",null]:check(not flags.consume({key:invalid}),"movement bits require booleans")
    flags.reset();check(not flags.swimming and flags.on_ground and flags.vertical_speed_mps==0,"teleport/logout resets locomotion flags")
    check(flags.consume({"swimming":false,"on_ground":false,"vertical_speed_mps":-8}) and flags.state(false)==0 and not flags.on_ground,"ordinary falling does not become swimming or flight")
    print(JSON.stringify({"passed":true,"checks":checks}));quit()
