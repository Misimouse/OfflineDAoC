"""Observe per-frame native remote attachments using real captured form rows.

No gameplay server is started. Reports a finding rather than accepting visuals.
"""
import argparse,copy,json,socket,subprocess,time
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def read(path):
    raw=path.read_bytes();return json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))

def probe(workspace,engine,proof,candidate=False):
    assert proof.resolve().is_relative_to((workspace/'RemoteModelRoundtripLab/RealProtocol').resolve())
    real=read(proof);assert real['passed'] and real['checks']['both_players_ordinary']
    trace_path=proof.parent/'remote_form_trace.json';snapshot_path=proof.parent/'active_snapshot.json'
    trace=read(trace_path);base=read(snapshot_path);local=next(r for r in base['entities'] if r['id']=='player:local')
    root=workspace/'RemoteModelEquipmentLab'/('CandidateProbe' if candidate else 'InstalledProbe')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');root.mkdir(parents=True)
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    project=workspace/'Client/DAoCBridgeClient.uproject'
    catalog=workspace/'models.json';gear=workspace/'equipment_catalog_v01.json'
    inputs={str(p):digest(p) for p in [proof,trace_path,snapshot_path,normal,catalog,gear]}
    if candidate:
        build_path=workspace/'RemoteModelEquipmentLab/native_build.json';build=read(build_path);assert build['passed'] and digest(normal)==build['normal_binary_sha256']
        project=Path(build['project']);binary=project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
        assert digest(binary)==build['binaries_sha256'][binary.name]
        inputs.update({str(p):digest(p) for p in [build_path,binary]})
    report=root/'native.json';process=None;peer=None;observations={}
    with socket.socket() as listener,(root/'engine.log').open('w',encoding='utf-8') as log:
        listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(.5)
        args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgePort='+str(listener.getsockname()[1]),'-DaocBridgeCatalog='+str(catalog),'-DaocBridgeEquipmentCatalog='+str(gear),'-DaocBridgeReport='+str(report),'-DaocBridgeProfile','-DaocBridgeProfileFixed','-DaocBridgeProfileSeconds=60','-nullrhi','-unattended','-nosound','-nosplash','-abslog='+str(root/'Unreal.log')]
        for key,file in [('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:args.append('-DaocBridge'+key+'='+str(root/file))
        try:
            process=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            deadline=time.monotonic()+120
            while peer is None:
                assert process.poll() is None,'Native probe exited before connection'
                assert time.monotonic()<deadline,'Native probe connection timed out'
                try:peer,_=listener.accept()
                except socket.timeout:pass
            peer.settimeout(.05);session='remote-equipment-probe'
            peer.sendall((json.dumps(dict(type='hello',protocol='daoc-visual-bridge',version=1,session=session))+'\n').encode())
            sequence=0
            states={k:copy.deepcopy(trace[k]) for k in ['original','transformed']}
            for model in [1884,1885]:
                row=copy.deepcopy(trace['transformed']);row['model_id']=model;states['form_'+str(model)]=row
            npc=copy.deepcopy(trace['transformed']);npc.update(id='npc:qa-form',kind='npc');states['npc_form_control']=npc
            states['restored']=copy.deepcopy(trace['restored'])
            for label,row in states.items():
                snapshot=copy.deepcopy(base)
                snapshot.update(session=session,status=label,entities=[copy.deepcopy(local),row])
                snapshot.pop('character_lobby',None)
                deadline=time.monotonic()+45
                while True:
                    # Real gateways publish continuously. A single frame goes
                    # stale during cold asset loading and deliberately clears
                    # native entities, invalidating attachment observations.
                    sequence+=1;snapshot['seq']=sequence
                    peer.sendall((json.dumps(snapshot)+'\n').encode())
                    assert process.poll() is None,'Native probe exited during observation'
                    try:
                        value=read(report)
                        if value.get('status')==label:
                            observations[label]=value.get('equipment_visual',{});break
                    except (OSError,ValueError):pass
                    assert time.monotonic()<deadline,'No per-frame equipment report for '+label
                    try:peer.recv(65536)
                    except socket.timeout:pass
                    time.sleep(.1)
            process.wait(timeout=90);assert process.returncode==0
        finally:
            if peer:peer.close()
            if process and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=20)
                except subprocess.TimeoutExpired:process.kill();process.wait()
    assert all(digest(Path(p))==sha for p,sha in inputs.items())
    assert observations['original'].get('remote_visible_count')==2 and observations['restored'].get('remote_visible_count')==2
    assert observations['npc_form_control'].get('remote_visible_count')==2
    installed_receipt=workspace/'RemoteModelEquipmentLab/installed.json'
    expect_fixed=candidate or (installed_receipt.exists() and read(installed_receipt).get('installed',False))
    if expect_fixed:assert all(observations[k].get('remote_visible_count')==0 for k in ['transformed','form_1884','form_1885'])
    result=dict(passed=True,candidate=candidate,observations=observations,source_inputs=inputs,normal_runtime_modified=False,real_server_started=False,rendered_acceptance=False,
        morph_has_visible_weapon_bindings=observations['transformed'].get('remote_visible_count',0)>0,
        original_count=observations['original'].get('remote_visible_count',0),restored_count=observations['restored'].get('remote_visible_count',0))
    (root/'verified.json').write_text(json.dumps(result,indent=2));return {k:v for k,v in result.items() if k not in ['source_inputs','observations']}|dict(proof=str(root/'verified.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','engine','proof']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--candidate',action='store_true')
    a=p.parse_args();print(json.dumps(probe(a.workspace.resolve(),a.engine.resolve(),a.proof.resolve(),a.candidate)))
