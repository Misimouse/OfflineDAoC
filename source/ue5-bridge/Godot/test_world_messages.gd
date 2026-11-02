extends SceneTree
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func _initialize()->void:
    var state=load("res://chat_state.gd").new()
    var rows:Dictionary={"npc:900":{"id":"npc:900","kind":"npc","name":"annoying lucradan","position_m":[1,0,1]},"player:902":{"id":"player:902","kind":"player","name":"Celt","position_m":[2,0,2]}}
    check(state.observe("message",{"type":1,"text":'annoying lucradan says, "Nya, nya. Ha ha ha! He he he!"'},rows,"",Vector3.ZERO,100),"known creature speech routes out of chat")
    check(state.entries.is_empty() and state.bubbles.size()==1 and state.bubbles[0].entity_id=="npc:900","speech associates only the matching NPC entity")
    check(state.bubbles[0].text=="Nya, nya. Ha ha ha! He he he!","bubble keeps original English body without duplicated says prefix")
    state.observe("message",{"type":1,"text":'Celt says, "Hello"'},rows,"",Vector3.ZERO,200)
    check(state.entries.size()==1 and state.entries[0].kind=="say","player speech stays in chat")
    state.observe("message",{"type":3,"text":'(Region) You have entered Ardee.'},rows,"",Vector3.ZERO,300)
    check(state.entries.size()==2 and state.entries.back().kind=="group","player channels cannot masquerade as region notices")
    check(state.observe("message",{"type":0,"text":"(Region) You have entered Ardee."},rows,"",Vector3.ZERO,400),"entered area uses screen notice")
    check(state.entries.size()==2 and state.notices.back().text=="You have entered Ardee.","region prefix is removed only from the on-screen original text")
    state.observe("message",{"type":0,"text":"(Region) You have left Ardee."},rows,"",Vector3.ZERO,500)
    check(state.notices.back().text=="You have left Ardee.","left area uses screen notice")
    state.observe("message",{"type":0,"text":"(Region) You have left Ardee."},rows,"",Vector3.ZERO,501)
    check(state.notices.size()==2,"immediate duplicate region notice is suppressed")
    state.observe("message",{"type":0,"text":"You have entered Connacht."},rows,"",Vector3.ZERO,600)
    check(state.notices.back().text=="You have entered Connacht.","zone entry without region prefix also routes to screen")
    for type in [200,201,202,203]:
        check(state.observe("message",{"type":type,"text":"Screen notice"+str(type)},rows,"",Vector3.ZERO,700+type),"original centre message routed "+str(type))
    check(state.notices.size()==3,"screen notices are bounded")
    rows["npc:901"]={"id":"npc:901","kind":"npc","name":"annoying lucradan","position_m":[3,0,1]}
    state.observe("message",{"type":1,"text":'annoying lucradan says, "Ambiguous"'},rows,"npc:900",Vector3.ZERO,1000)
    check(state.notices.back().text=="annoying lucradan: Ambiguous" and state.bubbles.size()==1,"duplicate NPC names use a neutral screen fallback, never a guessed speaker")
    state.observe("message",{"type":1,"popup":true,"text":"Welcome [train] <literal> & text"},rows,"npc:900",Vector3.ZERO,1100)
    check(state.bubbles.size()==1 and state.bubbles[0].text=="Welcome [train] <literal> & text","dialogue bubble retains literal keywords and replaces this speaker's old bubble")
    state.observe("message",{"type":1,"popup":true,"text":"Unassociated popup"},rows,"",Vector3.ZERO,1200)
    check(state.notices.back().text=="Unassociated popup","popup without a known NPC uses screen fallback")
    var view:Dictionary=state.snapshot(1300)
    check(view.bubbles[0].age_ms==200 and view.entries.size()==2,"transport contains transient age without polluting history")
    check(state.snapshot(20000).bubbles.is_empty() and state.snapshot(20000).notices.is_empty(),"transient messages expire")
    state.observe("message",{"type":1,"text":'annoying lucradan says, "Before region change"'},rows,"",Vector3.ZERO,21000)
    state.observe("region_changed",{},rows,"",Vector3.ZERO,21100)
    check(state.bubbles.is_empty() and state.notices.is_empty() and state.entries.size()==2,"region reset clears world messages but preserves conversations")
    var report:={"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}
    var f:=FileAccess.open("res://../Reports/world_messages/godot_tests.json",FileAccess.WRITE);f.store_string(JSON.stringify(report));f.close();print(JSON.stringify(report));quit(0 if failures.is_empty() else 1)
