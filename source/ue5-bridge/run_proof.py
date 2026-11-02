"""Run actual Godot + actual Unreal in separate isolated processes, no account/server."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import hashlib
import json
import os
import socket
import subprocess
import time
import uuid
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
UE=ROOT.parent/'DAoC-Enhanced-Unreal'
ENGINE=Path(str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'))
INSTALL=Path(str(INSTALL))
GODOT=INSTALL/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe'
wire='--wire' in sys.argv
REPORTS=ROOT/'Reports'/('wire' if wire else 'transport');REPORTS.mkdir(exist_ok=True,parents=True)
map_path=UE/'Content/DAoC/Connacht_v01/Ardee_Nwiro_Prueba.umap'
digest=lambda:hashlib.sha256(map_path.read_bytes()).hexdigest()
before=digest()
run_id=uuid.uuid4().hex
ready_file=REPORTS/('receiver_ready_'+run_id+'.txt')
(REPORTS/'proof_summary.json').write_text(json.dumps(dict(passed=False,stage='running',run_id=run_id)))
with socket.socket() as probe:
    probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
env=dict(os.environ,DOTNET_ROOT=str(INSTALL/'tools/dotnet'),DOTNET_ROOT_X64=str(INSTALL/'tools/dotnet'),
         APPDATA=str(REPORTS/'isolated-save'),DAOC_BRIDGE_PROOF_PORT=str(port),DAOC_BRIDGE_READY_FILE=str(ready_file),
         DAOC_BRIDGE_REPORTS=str(REPORTS),DAOC_BRIDGE_RUN_ID=run_id)
ue_cmd=[str(ENGINE),str(UE/'DAoCEnhanced.uproject'),'-run=pythonscript',f'-script={ROOT / "proof_unreal.py"}',
        '-NullRHI','-nosound','-unattended','-nosplash',f'-abslog={REPORTS / "unreal_engine.log"}']
godot_cmd=[str(GODOT),'--headless','--path',str(ROOT/'Godot'),'--script','res://proof_sender.gd','--',
           f'--port={port}',f'--report={REPORTS / "godot_proof.json"}','--duration=22']
fixture=None
if wire:
    from wire_fixture import Fixture
    fixture=Fixture();fixture.start()
    godot_cmd=[str(GODOT),'--headless','--path',str(INSTALL/'new-client/godot'),'--script',str(ROOT/'Godot/wire_sender.gd'),'--',
               f'--port={port}',f'--wire-port={fixture.port}',f'--report={REPORTS / "godot_proof.json"}','--duration=22']
with (REPORTS/'unreal_stdout.log').open('w') as ue_log,(REPORTS/'godot_stdout.log').open('w') as godot_log:
    unreal_proc=subprocess.Popen(ue_cmd,cwd=UE,env=env,stdout=ue_log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    godot_proc=None
    try:
        # Start Godot only once the receiver begins, independent of map loading time.
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            if ready_file.exists():break
            if unreal_proc.poll() is not None:raise RuntimeError('Unreal exited before receiver initialization')
            time.sleep(.25)
        else:raise TimeoutError('Unreal initialization')
        godot_proc=subprocess.Popen(godot_cmd,cwd=ROOT/'Godot',env=env,stdout=godot_log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        unreal_proc.wait(timeout=80);godot_proc.wait(timeout=35)
        report=json.loads((REPORTS/'unreal_proof.json').read_text())
        sender=json.loads((REPORTS/'godot_proof.json').read_text())
        assert unreal_proc.returncode==0 and godot_proc.returncode==0
        assert report['run_id']==run_id, 'stale report'
        assert report['passed'] and sender['commands']>=4
        assert before==digest(), 'destination map changed while testing'
        summary=dict(passed=True,run_id=run_id,synthetic=True,actual_engines=True,map_hash_unchanged=True,
                     snapshots=report['snapshots'],acks=report['acks'],connections=sender['connections'],
                     position_error_cm=report['position_error_cm'],yaw_error_deg=report['yaw_error_deg'],server_connected=False,
                     visual_review=False,runtime_build=False)
        if wire:
            assert sender['events']>100 and sender['existing_network_decoder']
            summary.update(existing_network_decoder=True,decoded_events=sender['events'],fixture_packets=fixture.packets)
        (REPORTS/'proof_summary.json').write_text(json.dumps(summary,indent=2))
        print(json.dumps(summary,indent=2))
    except Exception as exc:
        (REPORTS/'proof_summary.json').write_text(json.dumps(dict(passed=False,run_id=run_id,error=str(exc)),indent=2))
        raise
    finally:
        for proc in [godot_proc,unreal_proc]:
            if proc is not None and proc.poll() is None:proc.terminate();proc.wait(timeout=20)
        if fixture:fixture.close()
