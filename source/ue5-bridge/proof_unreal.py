"""Automated actual-engine test. Load the destination read-only; never save it."""
import json
import os
import sys
import time
import traceback
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from unreal_editor_bridge import BridgeClient

report={'passed':False,'run_id':os.environ.get('DAOC_BRIDGE_RUN_ID'),'synthetic':True,'visual_review':False,'server_connected':False,
        'runtime_build':False,'map_saved':False,'errors':[]}
client=None
try:
    config=json.loads((ROOT/'bridge_config.json').read_text())
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert levels.load_level(config['destination_map']), 'destination map load failed'
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    report['destination_map']=world.get_path_name().split('.')[0]
    assert report['destination_map']==config['destination_map']
    client=BridgeClient(int(os.environ['DAOC_BRIDGE_PROOF_PORT']))
    unreal.log('BRIDGE_RECEIVER_READY')
    Path(os.environ['DAOC_BRIDGE_READY_FILE']).write_text('ready')
    start=time.monotonic();sent_for_connection=0;forced=False;timeout_tested=False
    while time.monotonic()-start<32:
        client.tick()
        if client.session and client.stats['reconnects']!=sent_for_connection:
            sent_for_connection=client.stats['reconnects']
            client.command('ping');client.command('select_preview',entity_id='proof:1')
        if client.stats['snapshots']>=35 and not forced:
            client.close();forced=True
        if forced and client.stats['snapshots']>=100 and client.stats['acks']>=4:
            # Actual server exit or stale timeout must remove all preview actors.
            if not client.actors and client.session is None:
                timeout_tested=True;break
        time.sleep(.02)
    report.update(client.stats)
    report.update(forced_reconnection=forced,disconnect_cleared=timeout_tested,
                  remaining_actors=len(client.actors))
    assert client.stats['snapshots']>=100, 'insufficient snapshots'
    assert client.stats['max_actors']==4 and client.stats['spawned']>4, 'entity lifecycle not exercised'
    assert client.stats['reconnects']>=2 and client.stats['acks']>=4, 'round trip/reconnection'
    assert client.stats['position_error_cm']<.01, 'coordinate mismatch'
    assert client.stats['yaw_error_deg']<.001, 'orientation mismatch'
    assert not client.stats['errors'], 'receiver errors'
    assert timeout_tested, 'disconnect cleanup not observed'
    report['passed']=True
except Exception:
    report['errors'].append(traceback.format_exc())
finally:
    if client:client.close()
    reports=Path(os.environ.get('DAOC_BRIDGE_REPORTS',str(ROOT/'Reports')))
    reports.mkdir(exist_ok=True,parents=True)
    (reports/'unreal_proof.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('DAOC_BRIDGE_PROOF '+json.dumps(report))
