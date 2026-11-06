extends RefCounted
## Native movement facts carried into the existing original Position/Heading API.
var swimming:=false
var on_ground:=true
var vertical_speed_mps:=0.0
func reset()->void:
    swimming=false;on_ground=true;vertical_speed_mps=0.0
func consume(value:Dictionary)->bool:
    var wet=value.get("swimming",false);var floor=value.get("on_ground",true)
    var vertical=value.get("vertical_speed_mps",0.0)
    if not wet is bool or not floor is bool:return false
    if not (vertical is float or vertical is int) or not is_finite(float(vertical)) or absf(float(vertical))>100:return false
    swimming=wet;on_ground=floor and not wet;vertical_speed_mps=float(vertical);return true
func state(sitting:bool)->int:
    # Never manufacture the sitting|swimming combination used as a death pose.
    return 0x10 if sitting else 0x04 if swimming else 0
