extends RefCounted
## Authoritative player vitals and attack-mode requests. No local damage or rewards.
var generation:=0
var revision:=0
var ready:=false
var vitals:Dictionary={}
var attack_on:=false
var attack_uncertain:=false
var posture_uncertain:=false
var pending:Dictionary={}
var posture_pending:Dictionary={}
var feedback:=""
var requests:=0
var rejected:=0
var status_events:=0
var mode_events:=0
var combat_events:=0
var last_combat:Dictionary={}

func reset()->void:
    generation+=1;revision+=1;ready=false;vitals.clear();attack_on=false;attack_uncertain=false;posture_uncertain=false;pending.clear();posture_pending.clear();feedback="";last_combat.clear()

func _percent(data:Dictionary,key:String)->int:
    var value=data.get(key,-1)
    if not (value is int or value is float) or not is_finite(float(value)) or float(value)!=floor(float(value)):return -1
    return int(value) if value>=0 and value<=100 else -1

func _point(data:Dictionary,key:String)->int:
    var value=data.get(key,-1)
    if not (value is int or value is float) or not is_finite(float(value)) or float(value)!=floor(float(value)) or float(value)<0 or float(value)>65535:return -1
    return int(value)

func alive()->bool:
    if not ready:return false
    if vitals.get("alive") is bool:return bool(vitals.alive)
    if bool(vitals.get("absolute_health_known",false)):return int(vitals.get("health",0))>0
    return int(vitals.get("health_pct",0))>0

func health_fraction()->float:
    if not ready:return 1.0
    if bool(vitals.get("absolute_health_known",false)) and int(vitals.get("max_health",0))>0:return clampf(float(vitals.get("health",0))/float(vitals.max_health),0.0,1.0)
    return clampf(float(vitals.get("health_pct",0))*.01,0.0,1.0)

func consume(kind:String,data:Dictionary,me:int,now:int)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if kind=="status":
        var health:=_percent(data,"health_pct")
        if health<0:return
        var next:Dictionary={"health_pct":health,"mana_pct":maxi(0,_percent(data,"mana_pct")),"endurance_pct":maxi(0,_percent(data,"endurance_pct")),"conc_pct":maxi(0,_percent(data,"conc_pct")),"sitting":(int(data.get("sitting",0))&2)!=0}
        for key in ["health","max_health","mana","max_mana","endurance","max_endurance","conc","max_conc"]:next[key]=maxi(0,_point(data,key))
        next["absolute_health_known"]=_point(data,"health")>=0 and _point(data,"max_health")>0
        next["alive"]=int(next.health)>0 if next.absolute_health_known else health>0
        if not ready or vitals!=next:vitals=next;ready=true;revision+=1
        if posture_uncertain:posture_uncertain=false;revision+=1
        if not posture_pending.is_empty() and bool(posture_pending.on)==bool(next.sitting):posture_pending.clear();feedback="";revision+=1
        status_events+=1
        if not alive():
            if attack_on or attack_uncertain or not pending.is_empty() or not posture_pending.is_empty():attack_on=false;attack_uncertain=false;posture_uncertain=false;pending.clear();posture_pending.clear();revision+=1
    elif kind=="attack_mode":
        mode_events+=1
        attack_on=bool(data.get("on",false));attack_uncertain=false;pending.clear();feedback="";revision+=1
    elif kind=="combat":
        combat_events+=1
        last_combat={"attacker":int(data.get("attacker",0)),"defender":int(data.get("defender",0)),"weapon":int(data.get("weapon",0)),"style":int(data.get("style",0)),"result":int(data.get("result",0)),"at_ms":now}
        # BowPrepare is an animation announcement, not a hit/health update.
        if int(data.get("style",0))==0x3E80:return
        var health:=_percent(data,"health")
        if me>0 and int(data.get("defender",0))==me and health>=0 and ready:
            var was_alive:=alive()
            if int(vitals.health_pct)!=health:vitals.health_pct=health;vitals.absolute_health_known=false;revision+=1
            # A rounded combat percentage cannot announce a local death or revive.
            vitals["alive"]=was_alive
            if not was_alive:attack_on=false;attack_uncertain=false;posture_uncertain=false;pending.clear();posture_pending.clear();revision+=1
    elif kind=="death" and me>0 and int(data.get("oid",0))==me:
        vitals["health_pct"]=0;vitals["health"]=0;vitals["alive"]=false;vitals["absolute_health_known"]=true;ready=true;attack_on=false;attack_uncertain=false;posture_uncertain=false;pending.clear();posture_pending.clear();revision+=1
    elif kind=="revive" and me>0 and int(data.get("oid",0))==me:
        # PlayerInit sends real points BEFORE Revive. Keep those confirmed
        # positive vitals; if still dead/unknown, wait for actual Status.
        ready=alive();pending.clear();posture_pending.clear();attack_on=false;attack_uncertain=false;posture_uncertain=false;revision+=1

func observe_target_death(kind:String,data:Dictionary,selected:String,oid_map:Dictionary,entities:Dictionary,client:Node,now:int)->bool:
    if selected.is_empty() or not (attack_on or bool(pending.get("on",false))):return false
    if not pending.is_empty() and not bool(pending.get("on",false)):return false
    var oid:=-1;var dead:=false
    if kind=="remove" and int(data.get("type",1))==0:oid=int(data.get("oid",-1));dead=true
    elif kind=="death":oid=int(data.get("oid",-1));dead=true
    elif kind in ["move","combat"]:
        if kind=="combat" and int(data.get("style",0))==0x3E80:return false
        oid=int(data.get("defender" if kind=="combat" else "oid",-1));dead=_percent(data,"health")==0
    if not dead or String(oid_map.get(oid,""))!=selected:return false
    # Stop via the original protocol; retain authoritative mode until its ACK.
    return execute({"action":"combat_attack","on":false},client,selected,entities,now)

func advance(now:int)->void:
    if not pending.is_empty() and now>=int(pending.until_ms):
        pending.clear();attack_uncertain=true;feedback="Attack mode confirmation has not arrived.";revision+=1
    if not posture_pending.is_empty() and now>=int(posture_pending.until_ms):
        posture_pending.clear();posture_uncertain=true;feedback="Posture confirmation has not arrived.";revision+=1

func run_speed_mps(percent:int)->float:
    if posture_uncertain or bool(posture_pending.get("on",false)):return 0.0
    if ready and (not alive() or bool(vitals.get("sitting",false))):return 0.0
    return 4.775*clampf(float(percent)/100.0,0.0,3.0)

func fail(text:String)->bool:
    feedback=text;rejected+=1;revision+=1;return false

func execute(value:Dictionary,client:Node,selected:String,entities:Dictionary,now:int,before_attack:Callable=Callable())->bool:
    var action:=String(value.get("action",""))
    if action not in ["combat_attack","player_sit"]:return false
    var on=value.get("on")
    if not on is bool:return fail("Invalid attack mode.")
    if action=="player_sit":
        var epoch=value.get("player_generation",-1)
        if not (epoch is int or epoch is float) or not is_finite(float(epoch)) or float(epoch)!=float(generation):return fail("Character state has changed.")
        if not alive():return fail("You cannot change posture now.")
        if on and posture_uncertain:return fail("Request standing before sitting again.")
        if not posture_pending.is_empty() and on:return fail("Wait for the server response.")
        if bool(vitals.get("sitting",false))==on and posture_pending.is_empty() and not posture_uncertain:return true
        client.call("Sit",on);requests+=1;posture_pending={"on":on,"until_ms":now+4000};feedback="Waiting for server confirmation...";revision+=1;return true
    if on:
        var epoch=value.get("player_generation",-1)
        if not (epoch is int or epoch is float) or not is_finite(float(epoch)) or float(epoch)!=float(generation):return fail("Character state has changed.")
        if not ready:return fail("Wait for character state.")
        if attack_uncertain:return fail("Request stopping the attack before starting again.")
        if not alive():return fail("You cannot attack while dead.")
        if not pending.is_empty():return fail("Wait for the server response.")
        var id:=String(value.get("entity_id",""))
        if id!=selected or (not id.is_empty() and not entities.has(id)):return fail("The target has changed.")
        # As in the original client, drawing a weapon without a target is valid.
        # Faction, range, weapon, resources and attack results belong to the server.
        if attack_on:return true
    elif not attack_on and pending.is_empty() and not attack_uncertain:return true
    if on and before_attack.is_valid():before_attack.call()
    client.call("Attack",on);requests+=1;pending={"on":on,"until_ms":now+4000};feedback="Waiting for server confirmation...";revision+=1;return true

func snapshot()->Dictionary:
    return {"generation":generation,"revision":revision,"ready":ready,"vitals":vitals,"attack_on":attack_on,"attack_uncertain":attack_uncertain,"attack_pending":not pending.is_empty(),"attack_requested_on":bool(pending.get("on",false)),"posture_uncertain":posture_uncertain,"posture_pending":not posture_pending.is_empty(),"posture_requested_sitting":bool(posture_pending.get("on",false)),"feedback":feedback}
