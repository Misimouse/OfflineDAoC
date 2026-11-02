"""Engine-neutral protocol. Uses metres in Godot X/Y-up/Z coordinates, zone 207 only."""
import json
import math

MAX_FRAME = 1048576
ORIGIN = (1364., 130., 1263.)

def to_unreal(point):
    x,y,z = point
    return ((x-ORIGIN[0])*100, (z-ORIGIN[2])*100, (y-ORIGIN[1])*100)

def from_unreal(point):
    x,y,z = point
    return (x/100+ORIGIN[0], z/100+ORIGIN[1], y/100+ORIGIN[2])

def yaw_degrees(forward):
    return math.degrees(math.atan2(forward[1],forward[0]))

class Decoder:
    def __init__(self): self.buffer = bytearray()
    def feed(self, chunk):
        self.buffer.extend(chunk)
        if len(self.buffer)>MAX_FRAME: raise ValueError('frame limit')
        result=[]
        while b'\n' in self.buffer:
            end=self.buffer.index(10)
            line=bytes(self.buffer[:end]);del self.buffer[:end+1]
            obj=json.loads(line)
            if not isinstance(obj,dict): raise ValueError('object required')
            result.append(obj)
        return result

def validate_snapshot(message):
    if message.get('type')!='snapshot' or message.get('protocol')!='daoc-visual-bridge' or message.get('version')!=1:
        raise ValueError('protocol')
    if message.get('zone_id')!=207 or tuple(message.get('origin_m',()))!=ORIGIN: raise ValueError('calibration')
    if not isinstance(message.get('session'),str) or not message['session']: raise ValueError('session')
    seq=message.get('seq')
    if isinstance(seq,bool) or not isinstance(seq,(float,int)) or not math.isfinite(seq) or seq<1 or int(seq)!=seq:
        raise ValueError('sequence')
    rows=message.get('entities')
    if not isinstance(rows,list) or len(rows)>2048: raise ValueError('entities')
    seen=set()
    for row in rows:
        if not isinstance(row,dict): raise ValueError('entity')
        ident=row.get('id')
        if not isinstance(ident,str) or not ident or len(ident)>128 or ident in seen: raise ValueError('identity')
        seen.add(ident)
        if row.get('kind') not in ('player','npc'): raise ValueError('kind')
        for key,size in [('position_m',3),('forward_xz',2)]:
            value=row.get(key)
            if not isinstance(value,list) or len(value)!=size or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>100000 for v in value):
                raise ValueError(key)
        if math.hypot(*row['forward_xz'])<0.0001: raise ValueError('zero forward')
    return rows
