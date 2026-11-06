extends SceneTree
var checks:=0
func check(value:bool,label:String)->void:
    checks+=1
    if not value:push_error(label);quit(1);assert(false,label)
func _initialize()->void:
    var state=load(get_script().resource_path.get_base_dir().path_join("server_sound_state.gd")).new()
    state.configure({"7":{},"11":{},"12":{}})
    var event={"id":7,"zone":0,"x":0,"y":0,"z":0,"radius":0}
    var local:=Vector3(10,5,20)
    state.consume("sound_effect",event,207,local,100)
    check(state.events.size()==1 and not state.events[0].placed,"quest sound is non positional")
    state.consume("sound_effect",event,207,local,101)
    check(state.events.size()==2 and state.events[1].seq==2,"separate packets remain separate events")
    var placed={"id":12,"zone":207,"x":400,"y":800,"z":200,"radius":40}
    state.consume("sound_effect",placed,207,local,102)
    check(state.events.size()==3 and state.events[2].position_m==[10.0,5.0,20.0],"packet coordinates use original unit scale and axis order")
    placed.x=440;state.consume("sound_effect",placed,207,local,103)
    check(state.events.size()==4,"exact radius boundary audible")
    placed.x=441;state.consume("sound_effect",placed,207,local,104)
    check(state.events.size()==4,"outside source radius silent")
    placed.x=400;placed.zone=208;state.consume("sound_effect",placed,207,local,105)
    check(state.events.size()==4,"unloaded sound zone silent")
    placed.zone=208;placed.radius=0;state.consume("sound_effect",placed,207,local,106)
    check(state.events.size()==5 and not state.events[4].placed,"zero radius preserves original non positional fallback")
    state.consume("sound_effect",event,208,local,107)
    check(state.events.size()==5,"unrendered current zone silent")
    var bad=event.duplicate();bad.id=999;state.consume("sound_effect",bad,207,local,108)
    check(state.events.size()==5,"unknown sound has no substitute")
    for value in [-1,65536,0.5,NAN,"7",null]:
        bad=event.duplicate();bad.x=value;state.consume("sound_effect",bad,207,local,109)
        check(state.events.size()==5,"malformed packet silent")
    check(state.snapshot(1100).size()==5,"fresh events retained at one second boundary")
    check(state.snapshot(2100).is_empty(),"stale sounds cannot replay after late snapshot")
    state.consume("region_changed",{},207,local,2200)
    check(state.events.is_empty() and state.sequence==5,"reset clears events without reusing sequence ids")
    for i in 140:state.consume("sound_effect",event,207,local,3000+i)
    check(state.events.size()==128,"retention bounded")
    state.consume("quit",{},207,local,4000);check(state.events.is_empty(),"logout clears pending announcements")
    print(JSON.stringify({"passed":true,"checks":checks}));quit()
