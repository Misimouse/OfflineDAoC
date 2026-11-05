extends SceneTree
var checks:=0
var failures:Array=[]
class FakeClient extends Node:
    var calls:Array=[]
    func Command(text):calls.append(text)
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var state=load("res://gm_test_mode.gd").new();var client=FakeClient.new()
    check(not state.allows_test_transfer(200,202),"unconfirmed account cannot request test transfer")
    check(not state.ready and not state.combat_test,"default cannot claim combat mode")
    check(not state.request("combat",client,0) and client.calls.is_empty(),"unconfirmed state cannot enable combat")
    check(state.request("protected",client,0) and client.calls==["&bridgegm protected"],"entry explicitly requests protected server mode")
    check(not state.ready and not state.pending.is_empty(),"request never confirms itself")
    check(not state.request("combat",client,1),"pending request blocks toggle spam")
    state.consume("message",{"text":"someone said [DAOC_BRIDGE_GM] combat"});check(not state.ready,"unrelated text is not a server acknowledgement")
    state.consume("message",{"text":"[DAOC_BRIDGE_GM] invalid"});check(not state.ready,"unknown mode rejected")
    state.consume("message",{"text":"[DAOC_BRIDGE_GM] protected"});check(state.ready and not state.combat_test and state.pending.is_empty(),"protected server acknowledgement")
    check(state.allows_test_transfer(200,202),"confirmed protected GM may request transfer from another Hibernian area")
    check(not state.allows_test_transfer(100,202),"test transfer cannot pull another realm into Hibernia")
    check(not state.allows_test_transfer(200,207),"current native area keeps existing entry behavior")
    check(not state.allows_test_transfer(200,0),"unknown area cannot request test transfer")
    check(state.request("combat",client,10) and client.calls.back()=="&bridgegm combat","confirmed protected mode can request real combat")
    check(not state.combat_test,"combat enable waits for server")
    state.consume("message",{"text":"[DAOC_BRIDGE_GM] protected"});check(not state.combat_test and not state.feedback.is_empty(),"server refusal keeps protection and explains it")
    state.request("combat",client,20);state.consume("message",{"text":"[DAOC_BRIDGE_GM] combat"});check(state.combat_test and state.ready,"server confirms real combat state")
    check(not state.allows_test_transfer(200,202),"combat mode cannot cause an automatic test transfer")
    state.request("protected",client,30);check(state.combat_test,"protection request cannot pretend immunity before ACK")
    state.advance(5030);check(state.uncertain and state.pending.is_empty(),"missing ACK is visibly uncertain")
    check(not state.allows_test_transfer(200,202),"uncertain permissions never permit test transfer")
    check(not state.request("combat",client,5040),"uncertainty cannot enable combat")
    check(state.request("protected",client,5041),"protection remains recoverable after missing ACK")
    state.consume("message",{"text":"[DAOC_BRIDGE_GM] protected"});check(not state.uncertain and not state.combat_test,"server ACK restores confirmed protection")
    state.request("combat",client,6000);check(state.request("protected",client,6001),"F1 supersedes a pending combat enable immediately")
    state.consume("message",{"text":"[DAOC_BRIDGE_GM] combat"});check(state.pending=="protected" and state.combat_test,"late combat acknowledgement cannot cancel pending protection")
    state.consume("message",{"text":"[DAOC_BRIDGE_GM] protected"});check(state.pending.is_empty() and not state.combat_test,"protection acknowledged after superseded enable")
    state.consume("quit",{});check(not state.ready and state.pending.is_empty() and not state.combat_test,"logout clears confirmed mode")
    state.consume("you",{});check(not state.ready,"new entry never inherits previous session mode")
    var file=FileAccess.open("res://../Reports/gm_mode/godot_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures},"  "));file.close()
    print("GM_MODE_CHECKS ",checks," failures=",failures);client.free();quit(0 if failures.is_empty() else 1)
