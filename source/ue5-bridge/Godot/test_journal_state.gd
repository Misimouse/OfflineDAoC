extends SceneTree
class Server extends Node:
    var quests:Dictionary={}
    var commands:Array=[]
    func command(text:String)->void:commands.append(text)
class Client extends Node:
    var calls:Array=[]
    func RemoveQuest(index:int)->void:calls.append(index)
var count:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:count+=1;if not ok:failures.append(label)
func _initialize()->void:
    var model=load("res://journal_state.gd").new();var server:=Server.new();var client:=Client.new()
    model.sync(server,0);check(model.entries.is_empty(),"empty journal is not populated from an offline database")
    server.quests={3:{"name":"Third Quest (Level 8)","text":"[Step #2] Speak to [the guardian].\nDo not change <literal> text.","goals":[{"text":"Talk to the guardian","done":true},{"text":"Return to Ardee","done":false}]},1:{"name":"First Quest","text":"Original description","goals":[]}}
    model.sync(server,100);check(model.entries.size()==2 and model.entries[0].index==1 and model.entries[1].index==3,"journal indices sorted without renumbering")
    var quest:Dictionary=model.entries[1].duplicate(true);var request:={"action":"journal_remove","quest_index":3,"quest_token":quest.token}
    check(quest.text==server.quests[3].text and quest.goals[0].done and not quest.goals[1].done,"literal steps and goal completion preserved")
    model.sync(server,150);check(model.entries[1].token==quest.token,"unchanged server journal preserves identity")
    check(model.request(request,server,client,200) and client.calls==[2],"wire removal uses original zero-based index")
    check(model.entries.size()==2 and server.quests.size()==2,"request cannot remove a mission optimistically")
    check(not model.request(request,server,client,250) and client.calls.size()==1,"pending request cannot be repeated")
    model.sync(server,5300);check(model.pending.is_empty() and model.entries.size()==2,"unconfirmed removal expires without deleting journal entry")
    server.quests[3].text="[Step #3] Return";model.sync(server,5400);check(not model.request(request,server,client,5500),"changed mission invalidates open confirmation")
    server.quests[3]={"name":"Replacement mission","text":"New quest reusing journal slot","goals":[]};model.sync(server,5600);check(not model.request(request,server,client,5700),"reused index cannot abandon a replacement quest")
    for bad in [true,"3",1.5,NAN,INF,-1,0,256]:check(not model.request({"action":"journal_remove","quest_index":bad,"quest_token":model.entries[1].token},server,client,5800),"malformed quest index rejected")
    check(not model.request({"action":"journal_remove","quest_index":3,"quest_token":""},server,client,5900),"missing identity rejected")
    check(model.request({"action":"journal_guide"},server,client,6000) and server.commands==["/questguide"],"guide uses server ShowNext without task-giver side effect")
    check(model.guide.status=="pending","no invented guide while waiting")
    check(not model.observe("detail",{"caption":"Training sword","lines":["Item detail"]}),"item descriptions stay in original detail route")
    check(model.observe("detail",{"caption":"Quest Guide","lines":["Quest - page 1 of 2","[Step #1] Original text"]}) and model.guide.lines[1]=="[Step #1] Original text" and model.pending.is_empty(),"server guide bypasses item-prefetch cache and retains literal text")
    check(model.request({"action":"journal_guide_close"},server,client,6100) and model.guide.is_empty() and server.commands.size()==1,"close guide sends no game command")
    model.request({"action":"journal_guide"},server,client,6200);model.sync(server,11300);check(model.guide.status=="unavailable" and model.entries.size()==2,"missing guide response never fabricates a walkthrough")
    model.request({"action":"journal_guide_close"},server,client,11400)
    var row:Dictionary=model.entries[0];check(model.request({"action":"journal_remove","quest_index":row.index,"quest_token":row.token},server,client,11500),"current entry can request abandonment")
    server.quests.erase(1);model.sync(server,11600);check(model.entries.size()==1 and model.entries[0].index==3 and model.pending.is_empty(),"only server removal changes journal list")
    var stale:Dictionary=model.entries[0].duplicate(true);model.observe("you",{});model.sync(server,11700);check(not model.request({"action":"journal_remove","quest_index":3,"quest_token":stale.token},server,client,11800),"session change invalidates old confirmation")
    model.request({"action":"journal_guide"},server,client,11900);model.request({"action":"journal_guide_close"},server,client,11910);check(model.observe("detail",{"caption":"Quest Guide","lines":["Late response"]}) and model.guide.is_empty(),"closing pending guide suppresses late popup and protects item detail route")
    server.quests={1:{"name":"Ardee — A new beginning (Level 5)","text":"[Step #1] Speak to the guardian near Ardee.\nThe text and objectives below are simulated UI fixtures.","goals":[{"text":"Find the guardian","done":true},{"text":"Return safely to Ardee","done":false}]},3:{"name":"The ancient grove","text":"[Step #2] Return to the ancient grove.\nA second mission with a longer description to check wrapping and scrolling.","goals":[]}}
    model.sync(server,12000);model.feedback=""
    var fixture=JSON.parse_string(FileAccess.get_file_as_string(get_script().resource_path.get_base_dir().path_join("../Reports/ui_integration/fixture.json")));fixture.journal_fixture=true;fixture.classic_ui.character="Bridge Journal Fixture";fixture.classic_ui.journal=model.snapshot()
    var f:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/journal/fixture.json"),FileAccess.WRITE);f.store_string(JSON.stringify(fixture));f.close()
    var report:={"passed":failures.is_empty(),"checks":count,"failures":failures,"real_server":false,"real_quests_changed":0};var out:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/journal/godot_tests.json"),FileAccess.WRITE);out.store_string(JSON.stringify(report));out.close();print(JSON.stringify(report));server.free();client.free();quit(0 if failures.is_empty() else 1)
