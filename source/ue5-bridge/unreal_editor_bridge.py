"""UE editor proof only. Transient markers; no saved actors, map edits or gameplay input.

Execute this file from Unreal's Python console to start the optional preview.
The commandlet test imports BridgeClient and pumps it on the engine main thread.
"""
import json
import math
import socket
import time
from pathlib import Path
import unreal
from protocol import Decoder, validate_snapshot, to_unreal, yaw_degrees

ROOT=Path(__file__).resolve().parent

class BridgeClient:
    def __init__(self,port=19727):
        self.port=port;self.sock=None;self.decoder=Decoder();self.outbox=bytearray()
        self.session=None;self.seq=0;self.last_snapshot=0.;self.retry_at=0.
        self.actors={};self.subsystem=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.mesh=unreal.load_asset('/Engine/BasicShapes/Cylinder.Cylinder')
        if not self.mesh:raise RuntimeError('test marker mesh unavailable')
        self.stats=dict(snapshots=0,spawned=0,removed=0,reconnects=0,acks=0,
                        position_error_cm=0.,yaw_error_deg=0.,errors=[],source=None,max_actors=0)
        self.next_id=0

    def clear(self):
        for actor in self.actors.values():
            if unreal.SystemLibrary.is_valid(actor):self.subsystem.destroy_actor(actor)
        self.stats['removed']+=len(self.actors);self.actors.clear()

    def close(self):
        if self.sock:
            try:self.sock.close()
            except OSError:pass
        self.sock=None;self.decoder=Decoder();self.outbox.clear();self.session=None;self.seq=0
        self.clear();self.retry_at=time.monotonic()+.5

    def command(self,action,**values):
        if not self.session:return
        self.next_id+=1
        message=dict(type='command',session=self.session,id=f'preview:{self.next_id}',action=action,**values)
        data=(json.dumps(message,separators=(',',':'))+'\n').encode()
        if len(self.outbox)+len(data)>65536:raise ValueError('outgoing command limit')
        self.outbox.extend(data)

    def apply(self,message):
        rows=validate_snapshot(message)
        if message['session']!=self.session:raise ValueError('snapshot before handshake')
        if message['seq']<=self.seq:return
        self.seq=message['seq'];self.last_snapshot=time.monotonic();self.stats['source']=message.get('source')
        expected={row['id'] for row in rows}
        for ident in list(self.actors):
            if ident not in expected:
                self.subsystem.destroy_actor(self.actors.pop(ident));self.stats['removed']+=1
        for row in rows:
            point=to_unreal(row['position_m'])
            rotation=unreal.Rotator(pitch=0.,yaw=yaw_degrees(row['forward_xz']),roll=0.)
            actor=self.actors.get(row['id'])
            if actor is None:
                actor=self.subsystem.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*point),rotation,transient=True)
                if actor is None:raise RuntimeError('cannot spawn transient marker')
                actor.set_actor_label('BridgePreview_'+row['id'])
                actor.static_mesh_component.set_static_mesh(self.mesh)
                actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                actor.set_actor_scale3d(unreal.Vector(.5,.5,1.8))
                self.actors[row['id']]=actor;self.stats['spawned']+=1
            actor.set_actor_location(unreal.Vector(*point),False,True);actor.set_actor_rotation(rotation,True)
            actual=actor.get_actor_location()
            error=math.dist(point,(actual.x,actual.y,actual.z))
            self.stats['position_error_cm']=max(error,self.stats['position_error_cm'])
            actual_yaw=actor.get_actor_rotation().yaw
            yaw_error=abs((actual_yaw-yaw_degrees(row['forward_xz'])+180)%360-180)
            self.stats['yaw_error_deg']=max(yaw_error,self.stats['yaw_error_deg'])
        self.stats['snapshots']+=1;self.stats['max_actors']=max(self.stats['max_actors'],len(self.actors))

    def tick(self,delta=0.):
        now=time.monotonic()
        if self.sock is None:
            if now<self.retry_at:return
            candidate=socket.socket(socket.AF_INET,socket.SOCK_STREAM);candidate.settimeout(.03)
            try:candidate.connect(('127.0.0.1',self.port))
            except OSError:candidate.close();self.retry_at=now+.5;return
            candidate.setblocking(False);candidate.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
            self.sock=candidate;self.stats['reconnects']+=1
        try:
            if self.outbox:
                try:
                    sent=self.sock.send(self.outbox);del self.outbox[:sent]
                except BlockingIOError:pass
            # Main-thread work is bounded even with a noisy peer.
            messages=[]
            for _ in range(8):
                try:data=self.sock.recv(65536)
                except BlockingIOError:break
                if not data:self.close();return
                messages.extend(self.decoder.feed(data))
            if len(messages)>256:raise ValueError('message rate limit')
            newest=None
            for message in messages:
                kind=message.get('type')
                if kind=='hello':
                    if message.get('protocol')!='daoc-visual-bridge' or message.get('version')!=1 or message.get('zone_id')!=207:
                        raise ValueError('handshake')
                    if self.session!=message['session']:self.clear();self.seq=0
                    self.session=message['session'];self.last_snapshot=now
                elif kind=='snapshot':
                    validate_snapshot(message)
                    if newest is None or message['seq']>newest['seq']:newest=message
                elif kind=='ack':
                    if message.get('session')==self.session and message.get('ok') and message.get('forwarded_to_game') is False:
                        self.stats['acks']+=1
                else:raise ValueError('message type')
            if newest is not None:self.apply(newest)
            if self.session and now-self.last_snapshot>2.0:self.close()
        except (OSError,ValueError,KeyError,TypeError) as exc:
            self.stats['errors'].append(type(exc).__name__+': '+str(exc));self.close()

def start():
    previous=getattr(unreal,'_daoc_visual_bridge',None)
    if previous:
        unreal.unregister_slate_post_tick_callback(previous[1]);previous[0].close()
    config=json.loads((ROOT/'bridge_config.json').read_text())
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or world.get_path_name().split('.')[0]!=config['destination_map']:
        raise RuntimeError('Open the destination Ardee_Nwiro_Prueba map before starting the preview')
    client=BridgeClient(config['port']);handle=unreal.register_slate_post_tick_callback(client.tick)
    unreal._daoc_visual_bridge=(client,handle)
    unreal.log('DAoC visual bridge: preview markers only; no gameplay commands and no map saving')
    return client

if __name__=='__main__':start()
