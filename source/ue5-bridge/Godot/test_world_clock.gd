extends SceneTree
class ClockServer extends Node:
    var playing:=true
    var hour:float=-1.0
    func game_hour()->float:return hour
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var gateway=load("res://live_gateway.gd").new()
    var clock:=ClockServer.new()
    check(gateway.world_clock_snapshot()=={"ready":false},"no invented clock without server")
    var empty:=Node.new();gateway.server=empty
    check(gateway.world_clock_snapshot()=={"ready":false},"server must expose original game_hour helper")
    gateway.server=clock
    for hour in [-1.0,24.0,1000.0,INF,NAN]:
        clock.hour=hour
        check(gateway.world_clock_snapshot()=={"ready":false},"invalid or unknown original hour is not published")
    for hour in [0.0,5.5,6.0,12.5,18.0,23.99]:
        clock.hour=hour
        check(gateway.world_clock_snapshot()=={"ready":true,"hour":hour},"original numeric hour survives unchanged")
    clock.playing=false
    check(gateway.world_clock_snapshot()=={"ready":false},"lobby cannot retain previous world clock")
    var transport=load("res://visual_bridge.gd").new()
    clock.playing=true;clock.hour=12.5
    transport.snapshot_metadata["world_clock"]=gateway.world_clock_snapshot()
    check(transport.publish([]) and transport.last_snapshot.world_clock.hour==12.5,"actual transport carries original clock metadata")
    clock.playing=false;transport.snapshot_metadata["world_clock"]=gateway.world_clock_snapshot();transport.publish([])
    check(transport.last_snapshot.world_clock=={"ready":false},"logout snapshot clears previous clock readiness")
    var original=load("res://original_clock_helper.gd").new()
    check(original.game_hour()==-1.0,"unchanged original helper waits for time packet")
    # Copy of the exact installed helper, generated and hash-pinned by the runner.
    for sample in [[12.0,60,12.4],[0.0,60,0.5],[23.8,60,0.3],[5.9,60,6.32],[17.9,60,18.375]]:
        original.game_time_ms=int(float(sample[0])*3600000.0)
        original.game_time_at=Time.get_ticks_msec()-int(sample[1])*1000
        check(absf(original.game_hour()-float(sample[2]))<0.003,"original day/night rate and boundary interpolation")
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"server_started":false}
    var f:=FileAccess.open("res://verified_state.json",FileAccess.WRITE);f.store_string(JSON.stringify(report));f.close()
    print(JSON.stringify(report));gateway.server=null;gateway.free();clock.free();empty.free();transport.free();original.free();quit(0 if failures.is_empty() else 1)
