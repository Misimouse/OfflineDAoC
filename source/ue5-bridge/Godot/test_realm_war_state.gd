extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func ShowWarmap(code:int,page:int,keep:int)->void:calls.append([code,page,keep])
var checks:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:
    checks+=1
    if not ok:failures.append(label)
func packet(page:int=3)->Dictionary:
    return {"keeps":[{"map":page,"index":2,"tower":1,"realm":3,"claimed":true,"siege":false,"teleport":true,"guild":"Original guild"}],"relics":[1,2,3,1,2,3]}
func _initialize()->void:run.call_deferred()
func run()->void:
    var state=load(get_script().resource_path.get_base_dir().path_join("realm_war_state.gd")).new();var client:=Client.new()
    check(not state.snapshot().fights_ready and state.pages.is_empty(),"no invented ownership or empty battle map before server replies")
    check(not state.consume("warmap_keeps",packet()),"unsolicited ownership cannot open or populate a session")
    for page in [0,4,-1,1.5,"3",true,NAN,INF]:check(not state.request({"action":"warmap_request","page":page},client,true,1000),"reject invalid page %s"%str(page))
    check(not state.request({"action":"warmap_request","page":3},client,false,1000) and client.calls.is_empty(),"lobby cannot send a world map request")
    check(state.request({"action":"warmap_request","page":3},client,true,1000) and client.calls==[[0,3,0],[1,3,0]],"original page and update sequence uses Hibernia page three")
    check(not state.request({"action":"warmap_request","page":1},client,true,2100) and client.calls.size()==2,"no overlapping ambiguous page requests")
    check(not state.consume("warmap_keeps",packet(1)) and state.pages.is_empty(),"another realm reply cannot populate pending page")
    var bad:=packet();bad.keeps.append(bad.keeps[0])
    check(not state.consume("warmap_keeps",bad) and state.pages.is_empty(),"duplicate keep identity rejected atomically")
    bad=packet();bad.relics=[1,2,3]
    check(not state.consume("warmap_keeps",bad),"incomplete relic holders rejected")
    bad=packet();bad.keeps[0].claimed="true"
    check(not state.consume("warmap_keeps",bad),"string flag is not decoded server truth")
    check(state.consume("warmap_keeps",packet()) and state.pages["3"].keeps.has("358"),"original keep map index tower identity reconstructed")
    check(not state.snapshot().fights_ready,"keep reply does not invent a battle update")
    var fight:={"zone":214,"x":2,"y":3,"color":3,"size":1,"group":false}
    check(state.consume("warmap_fights",{"fights":[fight]}) and state.snapshot().fights_ready,"original battle quarter retained")
    fight.x=4
    check(not state.consume("warmap_fights",{"fights":[fight]}) and state.fights[0].x==2,"invalid quarter cannot replace valid battle cache")
    check(not state.request({"action":"warmap_request","page":1},client,true,1100),"rapid Update is throttled")
    check(not state.request({"action":"warmap_teleport","page":3},client,true,2200) and client.calls.size()==2,"information contract cannot request teleportation")
    check(state.request({"action":"warmap_request","page":1},client,true,2200),"next realm page can be requested after receipt")
    check(state.consume("warmap_keeps",{"keeps":[],"relics":[0,0,0,0,0,0]}) and state.pages["1"].ready and state.pages["1"].keeps.is_empty(),"genuine empty response marks only its own page ready")
    var view:Dictionary=state.snapshot();view.pages.clear();check(not state.pages.is_empty(),"snapshot cannot mutate state cache")
    check(state.request({"action":"warmap_request","page":2},client,true,3300),"Midgard uses original second page")
    state.maintain(13300);check(state.pending_page==-1 and not state.pages.has("2"),"timeout leaves unknown ownership unknown")
    check(not state.consume("warmap_keeps",packet(2)),"late response without pending request ignored")
    check(state.request({"action":"warmap_close"},client,true,14000) and not state.visible,"close sends no original gameplay action")
    check(state.consume("quit",{}) and state.pages.is_empty() and state.fights.is_empty() and not state.fights_ready,"logout clears all ownership and battle cache")
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"real_server":false}));client.free();quit(0 if failures.is_empty() else 1)
