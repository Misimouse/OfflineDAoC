extends SceneTree
class FakeServer extends Node:
    var playing:=true
    var entry:Dictionary={"zone":202,"region":200}
    var commands:Array=[]
    func command(text:String)->void:commands.append(text)
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var gateway=load("res://live_gateway.gd").new();var server:=FakeServer.new();gateway.server=server;gateway.player_state=load("res://player_combat_state.gd").new();gateway.gm_mode=load("res://gm_test_mode.gd").new()
    gateway.recover_test_region(100);check(server.commands.is_empty(),"unknown health cannot trigger a recovery transfer")
    gateway.player_state.ready=true;gateway.player_state.vitals={"health_pct":0};gateway.recover_test_region(100);check(server.commands.is_empty(),"death cannot trigger a false respawn")
    gateway.player_state.vitals.health_pct=25;gateway.recover_test_region(100);check(server.commands.is_empty(),"unconfirmed GM privilege cannot trigger GM transfer")
    gateway.gm_mode.ready=true;gateway.gm_mode.combat_test=true;gateway.recover_test_region(100);check(server.commands.is_empty(),"wait for protected confirmation")
    gateway.gm_mode.combat_test=false;gateway.gm_mode.pending="protected";gateway.recover_test_region(100);check(server.commands.is_empty(),"pending protection cannot transfer")
    gateway.gm_mode.pending="";gateway.recover_test_region(100);check(server.commands.size()==1 and server.commands[0].ends_with(" 200"),"real revival outside Connacht requests original GM transfer")
    check(gateway.player_state.vitals.health_pct==25 and server.entry.zone==202,"no health or region invented locally")
    gateway.recover_test_region(5099);check(server.commands.size()==1,"retry is rate limited")
    gateway.recover_test_region(5100);gateway.recover_test_region(10100);gateway.recover_test_region(15100);check(server.commands.size()==3,"failed transfer retries are bounded")
    server.entry.zone=207;gateway.recover_test_region(16000);check(server.commands.size()==3 and gateway.test_return_attempts==0,"Connacht acknowledgement stops recovery")
    server.entry.zone=202;gateway.leaving=true;gateway.recover_test_region(20000);check(server.commands.size()==3,"logout cannot trigger transfer")
    check(not server.commands.any(func(text):return "bind" in text or "release" in text),"bind and release commands are never rewritten")
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false};var file:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/release_camera/godot_tests.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report));file.close();print(JSON.stringify(report));gateway.free();server.free();quit(0 if failures.is_empty() else 1)
