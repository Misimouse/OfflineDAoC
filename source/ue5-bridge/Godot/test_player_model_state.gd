extends SceneTree
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var folder:String=get_script().resource_path.get_base_dir()
    var state=load(folder.path_join("player_model_state.gd")).new()
    var source:Dictionary={"302":{"race":"cel_m"},"310":{"race":"cel_f"},"1883":{"gltf":"original_celt_form"},"1884":{"gltf":"original_lur_form"},"999":{"gltf":"not_imported"}}
    state.configure(source,{"1883":{"type":"skeletal"},"1884":{"type":"skeletal"}});state.bind_base(1984)
    check(state.snapshot().model_id==1984 and not state.snapshot().morphed,"selected original figure is the initial model")
    state.consume("model_change",{"oid":77,"model":1883})
    check(not state.snapshot().morphed,"packets before the local identity cannot morph a character")
    state.consume("you",{"oid":77});state.consume("model_change",{"oid":88,"model":1883})
    check(not state.snapshot().morphed,"NPC model changes do not change the player")
    state.consume("model_change",{"oid":77,"model":999})
    check(state.snapshot().model_id==1984 and state.snapshot().missing_model and not state.snapshot().morphed,"missing native art retains the equipped figure instead of drawing a placeholder")
    state.consume("model_change",{"oid":77,"model":1883,"size":60})
    check(state.snapshot().model_id==1883 and state.snapshot().morphed and state.snapshot().size==60,"real local model packet activates an available original form and size")
    state.consume("model_change",{"oid":77,"model":302,"size":50})
    check(state.snapshot().model_id==1984 and not state.snapshot().morphed and state.snapshot().size==50,"original server race ID restores the selected native figure ID")
    state.consume("model_change",{"oid":77,"model":1884|0x8000})
    check(state.snapshot().model_id==1884,"original model flag is masked before catalogue lookup")
    state.consume("model_change",{"oid":77,"model":NAN});state.consume("model_change",{"oid":77,"model":0})
    check(state.snapshot().model_id==1884,"invalid model values cannot erase the active form")
    state.consume("region_changed",{});state.consume("model_change",{"oid":77,"model":1883})
    check(not state.snapshot().morphed and state.snapshot().model_id==1984,"region reset prevents stale local identity packets")
    state.consume("quit",{});check(state.snapshot().model_id==0,"saved logout clears the previous character model")
    state.bind_base(310);state.consume("you",{"oid":99});state.consume("model_change",{"oid":77,"model":1883})
    check(state.snapshot().model_id==310 and not state.snapshot().morphed,"another character cannot inherit the previous identity's morph")
    state.consume("model_change",{"oid":99,"model":1883});state.consume("model_change",{"oid":99,"model":310})
    check(state.snapshot().model_id==310 and not state.snapshot().morphed,"reversion also works for another race/sex native base")
    check(source["1883"].gltf=="original_celt_form" and source.size()==5,"model observations never rewrite original source metadata")
    var report:Dictionary={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}
    print(JSON.stringify(report));quit(0 if failures.is_empty() else 1)
