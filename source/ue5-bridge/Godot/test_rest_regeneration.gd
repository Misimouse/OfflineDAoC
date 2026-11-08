extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func Sit(on:bool)->void:calls.append(on)
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var model=load("res://player_combat_state.gd").new();var client:=Client.new()
    var status:={"health_pct":0,"health":1,"max_health":336,"mana_pct":1,"mana":1,"max_mana":200,"endurance_pct":1,"endurance":1,"max_endurance":100,"conc_pct":100,"sitting":0}
    model.consume("status",status,1,0)
    check(model.alive() and model.vitals.health==1,"positive original health permits rest despite zero percent")
    check(model.execute({"action":"player_sit","on":true,"player_generation":model.generation},client,"",{},1),"rest uses original Sit request")
    check(client.calls==[true] and not model.vitals.sitting,"request alone cannot confirm posture")
    model.advance(3000)
    check(model.vitals.health==1 and model.vitals.mana==1 and model.vitals.endurance==1,"elapsed time cannot grant local resources")
    status.sitting=2;model.consume("status",status,1,3001)
    check(model.vitals.sitting and not model.snapshot().posture_pending,"original server confirms seated state")
    model.advance(200000)
    check(model.vitals.health==1 and model.vitals.mana==1 and model.vitals.endurance==1,"seated client cannot simulate regeneration without packets")
    status.health=8;status.health_pct=2;status.mana=7;status.mana_pct=3;status.endurance=5;status.endurance_pct=5
    model.consume("status",status,1,200001)
    check(model.vitals.health==8 and model.vitals.mana==7 and model.vitals.endurance==5,"only authoritative resource increases reach UI state")
    check(absf(model.health_fraction()-8.0/336.0)<0.00001,"UI health fraction preserves actual values")
    check(model.execute({"action":"player_sit","on":false,"player_generation":model.generation},client,"",{},200002),"stand uses original request")
    check(model.vitals.sitting and client.calls==[true,false],"standing also waits for confirmation")
    status.sitting=0;model.consume("status",status,1,200003)
    check(not model.vitals.sitting and model.vitals.health==8,"standing acknowledgement does not reset recovered health")
    model.consume("quit",{},1,200004)
    check(not model.ready and model.vitals.is_empty(),"saved logout clears resource and posture display")
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures}
    var f:=FileAccess.open("res://../Reports/rest_regeneration/godot_tests.json",FileAccess.WRITE);f.store_string(JSON.stringify(report));f.close()
    print(JSON.stringify(report));client.free();quit(0 if failures.is_empty() else 1)
