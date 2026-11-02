extends RefCounted
## A container opens only after the real inventory-window packet from the nearby keeper.
var valid:=false
var first:=0
var count:=0
var title:=""
var keeper_id:=""
var token:=""
var generation:=0
var feedback:=""
func reset()->void:
    generation+=1;valid=false;first=0;count=0;title="";keeper_id="";token="";feedback=""
func maintain(interaction:RefCounted,entities:Dictionary,pos:Vector3,alive:bool)->void:
    if not valid:return
    var row:Dictionary=entities.get(keeper_id,{})
    if not alive or keeper_id!=interaction.conversation_id or not interaction._valid(row) or interaction._distance(row,pos)>6:reset()
func observe(kind:String,d:Dictionary,interaction:RefCounted,entities:Dictionary,pos:Vector3)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if kind=="remove" and keeper_id!="" and int(d.get("oid",-1))==int(keeper_id.get_slice(":",1)) and int(d.get("type",1))!=9:reset();return
    if kind!="inventory":return
    var window:=int(d.get("window",0))
    if window in [5,6]:reset();return
    if window not in [3,4]:return
    var id:=String(interaction.conversation_id);var row:Dictionary=entities.get(id,{})
    if id.is_empty() or id!=interaction.selected_id or not interaction._valid(row) or interaction._distance(row,pos)>6:reset();return
    generation+=1;valid=true;keeper_id=id;first=110 if window==3 else 150;count=40 if window==3 else 100;title="VAULT" if window==3 else "ACCOUNT VAULT";feedback=""
    token=JSON.stringify([generation,id,first,count]).sha256_text()
func close(value:Dictionary)->bool:
    if not valid:return true
    if String(value.get("vault_token",""))!=token:return false
    reset();return true
func snapshot()->Dictionary:return {"valid":valid,"first":first,"count":count,"title":title,"keeper_id":keeper_id,"token":token,"open_serial":generation,"feedback":feedback}
