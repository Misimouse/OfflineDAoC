extends SceneTree
var checks:=0
var failures:Array=[]
func check(value:bool,label:String)->void:
    checks+=1
    if not value:failures.append(label)
func _initialize()->void:
    var folder:String=get_script().resource_path.get_base_dir()
    var audio=load(folder.path_join("combat_audio_state.gd")).new()
    audio.configure({}, {"445":{"sound_set":1},"19":{"sound_set":6},"700":{"sound_set":7}})
    var state=load(folder.path_join("weapon_mode_audio_state.gd")).new()
    var world:Dictionary={"player:local":{"model_id":310,"health":1.0,"state":"idle","position_m":[1364,130,1263]}}
    var inventory:Dictionary={"weapon_set":"standard","items":{10:{"model":445},12:{"model":19},13:{"model":700}}}
    var untouched:Dictionary=inventory.duplicate(true)
    state.consume("you",{},1,audio,world,inventory,1000)
    state.consume("attack_mode",{"on":false},1,audio,world,inventory,1001)
    check(audio.events.is_empty(),"login baseline never plays a false sheathe")
    state.consume("combat_attack",{"on":true},1,audio,world,inventory,1100)
    check(audio.events.is_empty() and not state.armed,"unconfirmed input cannot produce draw sound")
    state.consume("attack_mode",{"on":true},1,audio,world,inventory,1200)
    check(audio.events.size()==1 and audio.events[0].event=="activate" and audio.events[0].set==1,"confirmed standard weapon mode uses real main-hand set")
    state.consume("attack_mode",{"on":true},1,audio,world,inventory,1300)
    check(audio.events.size()==1,"repeated server ACK cannot stack draw sounds")
    state.consume("attack_mode",{"on":false},1,audio,world,inventory,1400)
    check(audio.events.size()==2 and audio.events.back().event=="deactivate" and audio.events.back().set==1,"confirmed stop uses original drawn weapon's sheathe set")
    state.consume("attack_mode",{"on":false},1,audio,world,inventory,1450)
    check(audio.events.size()==2,"repeated stopped mode remains quiet")
    inventory.weapon_set="twohand"
    state.consume("attack_mode",{"on":true},1,audio,world,inventory,1500)
    check(audio.events.back().set==6,"two-handed staff uses slot12 instead of remembered sword")
    inventory.weapon_set="standard"
    state.consume("attack_mode",{"on":false},1,audio,world,inventory,1600)
    check(audio.events.back().set==6,"changing selected slot cannot replace the sound of the previously drawn item")
    inventory.weapon_set="ranged"
    state.consume("attack_mode",{"on":true},1,audio,world,inventory,1700)
    check(audio.events.back().set==7,"an actual ranged-mode ACK resolves slot13")
    var count:int=audio.events.size()
    state.consume("death",{"oid":1},1,audio,world,inventory,1800)
    state.consume("attack_mode",{"on":false},1,audio,world,inventory,1801)
    check(audio.events.size()==count and not state.armed,"death followed by stopped mode is not an invented sheathe")
    state.consume("attack_mode",{"on":true},1,audio,world,inventory,1900)
    count=audio.events.size()
    state.consume("status",{"health_pct":0},1,audio,world,inventory,2000)
    state.consume("attack_mode",{"on":false},1,audio,world,inventory,2001)
    check(audio.events.size()==count and not state.armed,"fatal status also clears mode without sheathing a corpse")
    world["player:local"].health=0;world["player:local"].state="dead"
    state.consume("attack_mode",{"on":true},1,audio,world,inventory,2100)
    check(audio.events.size()==count and not state.armed,"already dead actor cannot start a draw voice")
    world["player:local"].health=1;world["player:local"].state="idle"
    inventory.items.clear()
    state.consume("attack_mode",{"on":true},1,audio,world,inventory,2200)
    state.consume("attack_mode",{"on":false},1,audio,world,inventory,2300)
    check(audio.events.size()==count,"empty equipped slot cannot invent a weapon sound")
    state.consume("quit",{},1,audio,world,inventory,2400)
    check(not state.armed and state.drawn_model==0,"logout resets draw state quietly")
    inventory=untouched.duplicate(true)
    state.consume("attack_mode",{"on":true},1,audio,world,inventory,2500)
    check(inventory==untouched,"audio never changes active equipment or inventory")
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"scope":"isolated local original AttackMode audio decisions"}))
    quit(0 if failures.is_empty() else 1)
