extends RefCounted
## Owned pet identity comes only from PetWindow. No creature is created by this module.
const COMMANDS={"aggressive":[1,0,0],"defensive":[2,0,0],"passive":[3,0,0],"follow":[0,1,0],"stay":[0,2,0],"attack":[0,0,1],"release":[0,0,2]}
const LABELS={"aggressive":"AGGRESSIVE","defensive":"DEFENSIVE","passive":"PASSIVE","follow":"FOLLOW","stay":"STAY","attack":"ATTACK","release":"RELEASE"}
const SHORT={"aggressive":"AGR","defensive":"DEF","passive":"PAS","follow":"FOL","stay":"STY","attack":"ATK","release":"REL"}
var valid:=false
var oid:=0
var generation:=0
var token:=""
var name:=""
var health:=-1.0
var aggro:=0
var walk:=0
var raw_icons:Array=[]
var effects:Array=[]
var entries:Array=[]
var feedback:=""
var last_order_at:=-1000
var requests:=0
var rejected:=0
func reset()->void:
    generation+=1;valid=false;oid=0;token="";name="";health=-1;aggro=0;walk=0;raw_icons.clear();effects.clear();entries.clear();feedback="";last_order_at=-1000
func observe(kind:String,d:Dictionary)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if kind!="pet_window":return
    var action:=int(d.get("action",0));var next_oid:=int(d.get("oid",0))
    if action==0:reset();return
    if action not in [1,2] or next_oid<1 or next_oid>65535:return
    if not valid or oid!=next_oid or action==2:
        generation+=1;name="";health=-1;last_order_at=-1000
    valid=true;oid=next_oid;token=JSON.stringify([generation,oid]).sha256_text();aggro=int(d.get("aggro",0));walk=int(d.get("walk",0));raw_icons=d.get("icons",[]).slice(0,8);feedback=""
func sync(server:Node,entities:Dictionary,ids:Dictionary)->void:
    entries.clear();effects.clear()
    if not valid:return
    var row:Dictionary=entities.get(String(ids.get(oid,"npc:%d" % oid)),{})
    name=String(row.get("name",""));health=float(row.get("health",-1.0));health=clampf(health,0,1) if health>=0 else -1
    for raw in raw_icons:
        var icon:Array=server.skill_icon("spell",int(raw));effects.append({"icon":int(icon[0]),"border":int(icon[1])})
    for command in COMMANDS:
        var entry:={"id":"petcmd:"+String(command),"kind":"petcmd","name":"PET: "+String(LABELS[command]),"label":LABELS[command],"short":SHORT[command],"icon":-1,"border":-1,"level":0,"line":"","item_token":"","pet_token":token,"command":command}
        entry["token"]=JSON.stringify(entry).sha256_text();entries.append(entry)
func fail(text:String)->bool:rejected+=1;feedback=text;return false
func request(value:Dictionary,client:Node,interaction:RefCounted,entities:Dictionary,now:int,alive:bool)->bool:
    if not valid or String(value.get("pet_token",""))!=token:return fail("The pet has changed or is no longer available.")
    if not alive:return fail("You cannot give commands while dead.")
    var command:=String(value.get("command",""))
    if not COMMANDS.has(command):return fail("Invalid pet command.")
    if now-last_order_at<150:return fail("Wait a moment before repeating the command.")
    if command=="attack":
        var id:=String(interaction.selected_id);var target:Dictionary=entities.get(id,{})
        if id.is_empty() or id=="player:local" or id=="npc:%d" % oid or target.is_empty() or not bool(target.get("targetable",true)) or float(target.get("health",0))<=0:return fail("Select a living target for your pet.")
        var target_oid:=int(id.get_slice(":",1))
        if target_oid<1 or target_oid>65535:return fail("Invalid pet target.")
        client.call("Target",target_oid,0x6000)
    var args:Array=COMMANDS[command];client.call("PetCommand",int(args[0]),int(args[1]),int(args[2]));last_order_at=now;requests+=1;feedback="Command sent.";return true
func snapshot()->Dictionary:return {"valid":valid,"oid":oid,"token":token,"name":name,"health":health,"aggro":aggro,"walk":walk,"effects":effects.duplicate(true),"entries":entries.duplicate(true),"feedback":feedback}
