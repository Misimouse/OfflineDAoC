extends SceneTree
class FakeClient extends Node:
    var calls:Array=[]
    func Target(oid:int,flags:int)->void:calls.append(["target",oid,flags])
    func Interact(oid:int,x:int,y:int)->void:calls.append(["interact",oid,x,y])
    func Command(text:String)->void:calls.append(["command",text])
    func DialogResponse(a:int,b:int,c:int,code:int,answer:int)->void:calls.append(["dialog",a,b,c,code,answer])
var failures:Array=[]
var checks:=0
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var state=load("res://interaction_state.gd").new()
    var client:=FakeClient.new()
    var pos:=Vector3(1400,130,1250)
    var rows:Dictionary={"npc:2":{"id":"npc:2","kind":"npc","name":"Merchant","health":.42,"level":20,"position_m":[1402,130,1250]},"player:3":{"id":"player:3","kind":"player","name":"Remote","health":1,"position_m":[1401,130,1250]}}
    check(state.execute({"action":"target","entity_id":"npc:2"},client,rows,pos),"select NPC")
    check(client.calls.back()==["target",2,0xE000],"examine and in-view flags")
    rows["npc:2"].position_m=[1408,130,1250]
    rows["npc:2"].motion={"at_ms":Time.get_ticks_msec()-1000,"speed_mps":4.0,"interval_ms":5000,"destination_m":[1400,130,1250]}
    check(state.execute({"action":"interact","entity_id":"npc:2"},client,rows,pos),"moving NPC uses current server route for interaction range")
    rows["npc:2"].erase("motion");rows["npc:2"].position_m=[1402,130,1250]

    check(is_equal_approx(state.snapshot(rows,pos).target.health,.42),"target health")
    check(state.execute({"action":"target","entity_id":"player:3"},client,rows,pos),"select remote player")
    check(not state.execute({"action":"interact","entity_id":"player:3"},client,rows,pos),"NPC interaction cannot use player")
    check(state.execute({"action":"interact","entity_id":"npc:2"},client,rows,pos),"interact nearby")
    check(client.calls.back()==["interact",2,35*8192+56000,51*8192+50000],"interaction uses region coordinates")
    state.consume("message",{"text":"Ask about [Hibernia] or [work].","popup":true},rows,100)
    state.consume("message",{"text":"Also [help].","popup":true},rows,100)
    check(state.talk.keywords==["Hibernia","work","help"] and state.talk.text.contains("Ask about"),"stacked popup keeps keywords")
    var reply:int=state.talk.id
    check(state.execute({"action":"keyword","reply_id":reply,"word":"work"},client,rows,pos),"valid keyword reply")
    check(client.calls.back()==["command","&whisper work"],"same whisper as original client")
    var before:=client.calls.size()
    check(not state.execute({"action":"keyword","reply_id":reply,"word":"/jump"},client,rows,pos),"unoffered keyword blocked")
    check(client.calls.size()==before,"invalid keyword not sent")
    state.consume("merchant",{"page":0,"window":0,"items":[{"index":1,"name":"Sword","price":12345}]},rows,101)
    state.consume("merchant",{"page":1,"window":0,"items":[{"index":1,"name":"Shield","price":500}]},rows,101)
    state.consume("merchant",{"page":0,"window":0,"items":[{"index":1,"name":"Sword","price":12345}]},rows,102)
    check(state.merchant.pages.size()==2 and state.merchant.pages["0"].size()==1,"merchant pages merge without duplicate items")
    state.maintain(client,rows,pos+Vector3(10,0,0))
    check(not state.merchant.is_empty(),"small distance change keeps catalog stable")
    check(not state.execute({"action":"keyword","reply_id":reply,"word":"work"},client,rows,pos+Vector3(10,0,0)),"stable window does not extend interaction reach")
    state.execute({"action":"target","entity_id":"player:3"},client,rows,pos)
    check(state.talk.is_empty() and state.merchant.is_empty(),"target change closes old conversation")
    check(not state.execute({"action":"keyword","reply_id":reply,"word":"work"},client,rows,pos),"stale keyword blocked")
    state.consume("dialog",{"text":"Accept quest?","type":2,"code":34,"data1":11,"data2":12,"data3":13},rows,104)
    var id:int=state.dialogs[0].id
    state.consume("dialog",{"text":"Accept quest?","type":2,"code":34,"data1":11,"data2":12,"data3":13},rows,104)
    check(state.dialogs.size()==1,"duplicate dialog suppressed")
    check(state.execute({"action":"dialog_response","dialog_id":id,"answer":0},client,rows,pos),"decline confirmation")
    check(client.calls.back()==["dialog",11,12,13,34,0],"dialog uses server data")
    before=client.calls.size()
    check(not state.execute({"action":"dialog_response","dialog_id":id,"answer":1},client,rows,pos) and client.calls.size()==before,"answered dialog cannot be replayed")
    check(not state.execute({"action":"interact","entity_id":"npc:2"},client,rows,pos+Vector3(20,0,0)),"distant NPC blocked")
    state.execute({"action":"target","entity_id":""},client,rows,pos)
    check(client.calls.back()==["target",0,0] and state.selected_id.is_empty(),"clear target sent")
    state.execute({"action":"target","entity_id":"npc:2"},client,rows,pos)
    rows.erase("npc:2");state.maintain(client,rows,pos)
    check(state.selected_id.is_empty() and client.calls.back()==["target",0,0],"removed target clears server selection")
    state.consume("dialog",{"text":"Note","type":0,"code":0},rows,105)
    state.consume("region_changed",{},rows,106)
    check(state.dialogs.is_empty() and state.messages.is_empty(),"region clears UI state")
    var f:=FileAccess.open("res://../Reports/interactions/godot_tests.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures},"  "));f.close()
    print("INTERACTION_CHECKS ",checks," failures=",failures)
    client.free();quit(0 if failures.is_empty() else 1)
