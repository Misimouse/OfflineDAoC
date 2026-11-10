"""Replay a real two-player form trace through the installed UE actor consumer.

This verifies actor replacement and lifetime, not rendered visual quality or
weapon attachment suppression. Those require separate native acceptance.
"""
import argparse,json,subprocess
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest

def verify(workspace,engine,proof):
    assert verify_files(workspace)['remote_model_size_installed']
    assert proof.resolve().is_relative_to((workspace/'RemoteModelRoundtripLab/RealProtocol').resolve())
    real=json.loads(proof.read_text());assert real['passed'] and all(real['checks'].values())
    assert real['checks']['both_players_ordinary'] and real['checks']['original_remote_bainshee_form']
    assert real['database_restored'] and real['normal_shutdown'] and real['normal_runtime_unchanged']
    trace_path=proof.parent/'remote_form_trace.json';trace=json.loads(trace_path.read_text())
    assert trace['original']['model_id']==trace['restored']['model_id']==310
    assert trace['transformed']['model_id']==1883
    assert len({r['id'] for r in trace.values()})==1 and all(r['size']==50 for r in trace.values())
    root=workspace/'RemoteModelRoundtripLab/Native'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');root.mkdir(parents=True)
    cases=[]
    for seq,label in enumerate(['original','transformed','restored'],1):
        # Keep the actual row, including authoritative equipment and motion.
        cases.append(dict(label=label,snapshot=dict(session='entity-acceptance',seq=seq,zone_id=207,origin_m=[1364,130,1263],in_game=True,entities=[trace[label]])))
    cases.append(dict(label='observer logout',snapshot=dict(session='entity-acceptance',seq=4,zone_id=207,origin_m=[1364,130,1263],in_game=False,entities=[])))
    fixture=root/'fixture.json';fixture.write_text(json.dumps(dict(cases=cases),indent=2))
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    catalog=workspace/'models.json';inputs={str(p):digest(p) for p in [normal,catalog,proof,trace_path,fixture]}
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(workspace/'Client/DAoCBridgeClient.uproject'),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeEntityTest='+str(fixture),'-DaocBridgeCatalog='+str(catalog),'-nullrhi','-unattended','-nosound','-nosplash','-abslog='+str(root/'engine.log')]
    for key,file in [('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:args.append('-DaocBridge'+key+'='+str(root/file))
    with (root/'stdout.log').open('w',encoding='utf-8') as log:run=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
    native=Path(str(fixture)+'.native.json');assert run.returncode==0 and native.exists(),str(root)
    result=json.loads(native.read_text(encoding='utf-8-sig'));assert result['passed'] and not result['failures'] and result['checks']>=30,result
    assert all(digest(Path(p))==h for p,h in inputs.items());verify_files(workspace)
    result.update(source_inputs=inputs,normal_runtime_modified=False,live_native_connection=False,rendered_acceptance=False,weapon_attachment_acceptance=False)
    (root/'verified.json').write_text(json.dumps(result,indent=2));return dict(passed=True,checks=result['checks'],proof=str(root/'verified.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','engine','proof']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.proof.resolve())))
