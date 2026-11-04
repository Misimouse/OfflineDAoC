extends RefCounted
## Original ModelChange packets, bounded to models actually available to the native renderer.
var source_models:Dictionary={}
var native_models:Dictionary={}
var base_model:=0
var local_oid:=-1
var requested_model:=0
var requested_size:=50

func configure(source:Variant,native:Variant)->void:
    source_models=source if source is Dictionary else {}
    native_models=native if native is Dictionary else {}

func bind_base(model:int)->void:
    base_model=model;local_oid=-1;requested_model=0;requested_size=50

func consume(kind:String,data:Dictionary)->void:
    if kind in ["region_changed","quit"]:
        local_oid=-1;requested_model=0;requested_size=50
        if kind=="quit":base_model=0
        return
    if kind=="you":
        local_oid=int(data.get("oid",-1));requested_model=0;requested_size=50;return
    if kind!="model_change" or local_oid<=0 or int(data.get("oid",-1))!=local_oid:return
    var value:Variant=data.get("model",0)
    if not (value is int or value is float) or not is_finite(float(value)) or float(value)!=floor(float(value)) or float(value)<1 or float(value)>65535:return
    var model:int=int(value)&0x7fff
    if model<=0:return
    requested_model=model
    var size:int=int(data.get("size",0))
    if size>0 and size<=1000:requested_size=size

func snapshot()->Dictionary:
    var result:Dictionary={"model_id":base_model,"source_model":requested_model,"size":50,"morphed":false,"missing_model":false}
    if requested_model<=0:return result
    var original:Dictionary=source_models.get(str(requested_model),{})
    # Original race models (without a monster glTF) restore the equipped figure.
    if not original.is_empty() and String(original.get("gltf",""))=="":return result
    var native:Dictionary=native_models.get(str(requested_model),{})
    if original.is_empty() or not String(native.get("type","")) in ["skeletal","static"]:
        result.missing_model=true;return result
    result.model_id=requested_model;result.size=requested_size;result.morphed=true
    return result
