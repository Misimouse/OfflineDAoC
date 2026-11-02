extends SceneTree
class ServerLocal extends Node:
    var entry:Dictionary={"zone":207,"zone_name":"Connacht"}
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var state=load("res://chat_state.gd").new()
    state.observe("message",{"type":1,"text":"You say, hello"});check(state.entries[0].kind=="say" and state.entries[0].source=="server","server speech retains original channel and provenance")
    state.observe("message",{"type":3,"text":"Group"});check(state.entries.back().kind=="group","group uses original channel code")
    state.observe("message",{"type":12,"text":"Group leader"});check(state.entries.back().kind=="group","group aliases remain in same channel")
    state.observe("message",{"type":4,"text":"Guild"});check(state.entries.back().kind=="guild","guild chat is distinct from system")
    state.observe("message",{"type":26,"text":"Coins"});check(state.entries.back().kind=="loot","loot and money keep original type")
    state.observe("message",{"type":17,"text":"Hit"});check(state.entries.back().kind=="combat","own combat remains distinct")
    state.observe("message",{"type":22,"text":"Other hit"});check(state.entries.back().kind=="combat_others","others combat remains filterable")
    state.observe("message",{"type":18,"text":"Damage"});check(state.entries.back().kind=="damage_taken","incoming damage has independent channel")
    state.observe("message",{"type":16,"text":"Spell"});check(state.entries.back().kind=="spells","spells have original channel")
    state.observe("message",{"type":1,"popup":true,"text":"NPC [keyword]"});check(state.notices.back().text=="NPC [keyword]","NPC popup speech retains literal dialogue keywords")
    var size:int=state.entries.size();state.observe("message",{"type":100,"text":"TE,1,0,0"});check(state.entries.size()==size and state.skipped_social==1,"structured social-window packet is not printed as raw chat")
    for type in [200,201]:state.observe("message",{"type":type,"text":"Zone title"})
    check(state.entries.size()==size,"center-only titles do not pollute conversation history")
    state.observe("message",{"type":202,"text":"Center and chat"});check(state.notices.back().text=="Center and chat","center warning uses temporary screen notice instead of history")
    state.observe("message",{"type":199,"text":"Unknown future type"});check(state.entries.back().kind=="system","unknown ordinary messages are preserved as system")
    var literal:='<red>Hello & "quoted"</> [keyword]\nSecond line';state.observe("message",{"type":0,"text":literal});check(state.entries.back().text==literal,"provider preserves literal markup characters, quotes and newlines")
    var long_text:="x".repeat(600);state.observe("message",{"type":0,"text":long_text});check(state.entries.back().text.length()==600,"normal long messages are no longer cut at 240 characters")
    state.observe("message",{"type":0,"text":"x".repeat(5000)});check(state.entries.back().text.length()==4096,"single message memory has an explicit upper bound")
    var frozen:Dictionary=state.snapshot();var frozen_count:int=frozen.entries.size();state.append("Local macro feedback","help")
    check(state.entries.back().source=="client" and state.entries.back().type==-1,"local client feedback is distinguishable from server messages")
    check(frozen.entries.size()==frozen_count,"published history view cannot mutate when another message arrives")
    var before:int=state.revision;state.observe("combat",{"text":"Not chat"});check(state.revision==before,"non-message world packets do not rebuild chat")
    state.append("", "system");check(state.revision==before,"empty message is ignored")
    for i in 240:state.append("Burst %d" % i,"combat")
    check(state.entries.size()==200 and state.entries[0].text=="Burst 40" and state.entries.back().text=="Burst 239","bounded history keeps the latest two hundred complete events")
    check(state.entries.back().id>state.entries[0].id,"monotonic message identity survives trimming")
    state.observe("region_changed",{});check(state.entries.size()==200,"changing regions preserves current-session conversations")
    state.observe("quit",{});check(state.entries.is_empty() and state.snapshot().entries.is_empty(),"logout clears previous-character history")
    var gateway=load("res://live_gateway.gd").new();var server:=ServerLocal.new();gateway.server=server;gateway.classic_ui=load("res://classic_ui_state.gd").new();gateway.chat_state=state;gateway.position=Vector3(1,2,3);gateway.heading=0
    check(gateway.dispatch_chat("/loc") and state.entries.back().kind=="system" and state.entries.back().text=="Connacht: loc=40,120,80 dir=0","client location command preserves original system channel and zone coordinates");gateway.free();server.free()
    var transport=load("res://visual_bridge.gd").new();transport.snapshot_metadata={"chat":state.snapshot(),"messages":["legacy"]};transport.publish([],207,"test")
    check(transport.last_snapshot.has("chat") and transport.last_snapshot.chat.entries.back().kind=="system" and transport.last_snapshot.messages==["legacy"],"actual outbound transport includes typed chat alongside compatible legacy messages");transport.free()
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false};var f:=FileAccess.open("res://../Reports/chat_channels/godot_tests.json",FileAccess.WRITE);f.store_string(JSON.stringify(report));f.close();print(JSON.stringify(report));quit(0 if failures.is_empty() else 1)
