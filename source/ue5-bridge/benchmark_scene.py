"""Repeatable rendering diagnostic using local spawn placements, without a game login."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json, math, os, socket, subprocess, threading, time, uuid, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
GAME=Path(str(INSTALL / 'new-client/godot'))
REPORT=ROOT/'Reports/performance';REPORT.mkdir(parents=True,exist_ok=True)

def main():
    config=json.loads((ROOT/'bridge_config.json').read_text())
    view='ardee' if '--view=ardee' in sys.argv else 'forest'
    if view=='ardee':
        config['initial_spawn_m']=[1357,130,1244.2]
        config['initial_camera_yaw_deg']=-106.7
    catalog=json.loads((ROOT/'models.json').read_text())
    point=config['initial_spawn_m']
    spawns=json.loads((GAME/'content/zones/zone207/npcs.json').read_text())['spawns']
    spawns=sorted((s for s in spawns if str(s['model']) in catalog and catalog[str(s['model'])].get('type')!='hidden'),
                  key=lambda s:(s['pos'][0]-point[0])**2+(s['pos'][2]-point[2])**2)[:200]
    rows=[]
    for i,s in enumerate(spawns):
        a=s.get('heading',0)*math.tau/4096
        rows.append(dict(id=f'npc:{i+1}',kind='npc',name=s['name'],model_id=int(s['model']),size=s.get('size',50),
                         position_m=s['pos'],forward_xz=[math.sin(a),math.cos(a)],state='idle',health=1))
    player=dict(id='player:local',kind='player',name='Diagnostic preview',model_id=0,
                position_m=point,forward_xz=[1,0],state='idle',health=1)
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(1)
    stop=threading.Event();session=uuid.uuid4().hex
    def serve():
        while not stop.is_set():
            try:peer,_=listener.accept()
            except socket.timeout:continue
            except OSError:break
            with peer:
                peer.setblocking(False);peer.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                def encode(obj):return (json.dumps(obj,separators=(',',':'))+'\n').encode()
                try:
                    pending=encode(dict(type='hello',protocol='daoc-visual-bridge',version=1,session=session))
                    seq=0;buffer=b''
                    while not stop.is_set():
                        seq+=1
                        if not pending:pending=encode(dict(type='snapshot',protocol='daoc-visual-bridge',version=1,session=session,
                                  seq=seq,zone_id=207,origin_m=[1364,130,1263],entities=rows+[player],
                                  character='Diagnostic preview',status='Rendering diagnostic (no server login)'))
                        try:pending=pending[peer.send(pending):]
                        except BlockingIOError:pass
                        try:
                            chunk=peer.recv(65536)
                            if not chunk:break
                            buffer+=chunk
                            while b'\n' in buffer:
                                line,buffer=buffer.split(b'\n',1);cmd=json.loads(line)
                                if cmd.get('action')=='move':player['position_m']=cmd['position_m']
                        except BlockingIOError:pass
                        time.sleep(.04)
                except (OSError,ValueError):pass
    thread=threading.Thread(target=serve,daemon=True);thread.start()
    quality=next((arg.split('=',1)[1] for arg in sys.argv if arg.startswith('--quality=')),'original')
    quick='--quick' in sys.argv
    navigation='--navigation' in sys.argv
    interactive='--interactive' in sys.argv
    label=(('ardee_' if view=='ardee' else '')+('quick_' if quick else 'diagnostic_')+quality)
    if navigation:label='navigation_'+quality
    if interactive:label='controls_'+quality
    output=REPORT/(label+'.json')
    command=[str(ENGINE / 'Binaries/Win64/UnrealEditor.exe'),str(ROOT/'Client/DAoCBridgeClient.uproject'),
             config['destination_map'],'-game','-DaocBridge','-DaocBridgeProfile','-DaocBridgeReadOnly',
             f'-DaocBridgePort={listener.getsockname()[1]}','-windowed','-ResX=1920','-ResY=1080','-d3d11','-nosplash',
             f'-DaocBridgeYaw={config["initial_camera_yaw_deg"]}',f'-DaocBridgeCatalog={ROOT/"models.json"}',
             f'-DaocBridgeQuality={quality}',
             f'-DaocBridgeFoliageCatalog={ROOT/"foliage_lods.json"}',
             f'-DaocBridgeCollisionCatalog={ROOT/"collision_catalog.json"}',
             f'-DaocBridgeCapture={REPORT/(view+"_"+quality+".png")}',
             f'-DaocBridgeHeights={GAME/"content/zones/zone207/heights.f32"}',f'-DaocBridgeReport={output}']
    if quick:command.append('-DaocBridgeProfileSeconds=30')
    if navigation or interactive:
        command.remove('-DaocBridgeReadOnly')
        command.append('-DaocBridgeNavigationProbe')
        command.append('-DaocBridgeProfileFixed')
    if navigation:command.extend(['-DaocBridgeAutoTest','-DaocBridgeAutoWalk','-DaocBridgeProfileSeconds=65'])
    try:
        with (REPORT/'diagnostic_stdout.log').open('w') as log:
            proc=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            proc.wait(timeout=330)
        data=json.loads(output.read_text(encoding='utf-8-sig'));samples=data.get('profile_samples',[]);groups={}
        # Ignore each phase's first three seconds after changing rendering settings.
        starts={}
        for sample in samples:starts.setdefault(sample['phase'],sample['elapsed'])
        for sample in samples:
            if sample['elapsed']-starts[sample['phase']]>3:groups.setdefault(sample['phase'],[]).append(sample)
        summary={'synthetic_entities':True,'real_game_server':False,'entities':len(rows),'map':data['map'],'quality':quality,'phases':{},'completed_profile':bool(samples)}
        for name,group in groups.items():
            def percentile(key,q):
                values=sorted(s[key] for s in group);return values[min(int((len(values)-1)*q),len(values)-1)]
            summary['phases'][name]=dict(samples=len(group),fps_median=1000/percentile('frame_ms',.5),
                frame_ms_p95=percentile('frame_ms',.95),**{key+'_median':percentile(key,.5) for key in ['bridge_ms','game_ms','render_ms','rhi_ms','gpu_ms']})
        (REPORT/(label+'_summary.json')).write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
    finally:
        stop.set();listener.close();thread.join(timeout=2)

if __name__=='__main__':main()
