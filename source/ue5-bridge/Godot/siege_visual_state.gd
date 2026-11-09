extends RefCounted
## Original SiegeWeaponAnimation body clips. No readiness, timer, damage or projectile simulation.
const MODELS:=[2598,2599,2600,2601,2602,2604,2605,2606,2607,2645]
var catalog:Dictionary={}
var events:Dictionary={}
var sequence:=0
func configure(models:Dictionary)->void:catalog=models
func supports(model:int)->bool:return model in MODELS and bool(catalog.get(str(model),{}).get("siege",false))
func reset()->void:events.clear()
func consume(kind:String,data:Dictionary,ids:Dictionary,entities:Dictionary,now:int)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    var id:String=String(ids.get(int(data.get("oid",0)),""))
    if kind in ["remove","death"]:events.erase(id);return
    if kind!="siege_anim" or id.is_empty() or not entities.has(id):return
    var row:Dictionary=entities[id];var model:=int(row.get("model_id",0));var definition:Dictionary=catalog.get(str(model),{})
    if model not in MODELS or not bool(definition.get("siege",false)) or String(row.get("state",""))=="dead":return
    var raw:Variant=data.get("action",-1)
    if typeof(raw) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(float(raw)) or float(raw)!=floor(float(raw)):return
    var clip:String={2:"load",3:"load",4:"fire"}.get(int(raw),"")
    if clip.is_empty() or not definition.has(clip):return
    sequence+=1
    events[id]={"seq":sequence,"at_ms":now,"model_id":model,"kind":"siege","clip":clip}
func snapshot(id:String,model:int,now:int)->Dictionary:
    var event:Dictionary=events.get(id,{})
    if event.is_empty():return {"events":[]}
    if model!=int(event.model_id) or now<int(event.at_ms) or now-int(event.at_ms)>8000:
        events.erase(id);return {"events":[]}
    var out:Dictionary=event.duplicate(true);out["age_ms"]=now-int(out.at_ms);out.erase("at_ms");out.erase("model_id")
    return {"events":[out]}
func prune(entities:Dictionary)->void:
    for id in events.keys():
        if not entities.has(id) or int(entities[id].get("model_id",0))!=int(events[id].model_id):events.erase(id)
