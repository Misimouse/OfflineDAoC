"""Replay original classic UI and player-state fixtures on the interface-key candidate."""
import argparse,json,shutil,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest
from verify_options_audio_native import read

def verify(workspace,engine,lab_name="InterfaceKeysLab",installed=False):
    assert lab_name in ["InterfaceKeysLab","OriginalControlsLab","KeyboardTurningLab"]
    root=workspace/lab_name;bp=root/'native_build.json';build=read(bp);assert build['passed']
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';before=digest(normal);assert before==(build['binaries_sha256'][normal.name] if installed else build['normal_binary_sha256'])
    output=root/('InstalledUIRegression' if installed else 'UIRegression')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True);reports={};inputs={str(bp):digest(bp)}
    for name,flag,origin in [('classic','DaocBridgeClassicTest',workspace/'Reports/ui_integration/fixture.json'),('player','DaocBridgePlayerStateTest',workspace/'Reports/player_release/native_fixture.json')]:
        target=output/(name+'.json');shutil.copy2(origin,target);inputs[str(origin)]=digest(origin)
        if name=='player':
            # This older native fixture simulates death by editing health_pct.
            # Its captured positive absolute HP must not contradict that simulation.
            # Test the legacy percentage-only path here; the separate vitals
            # acceptance retains the real positive-HP/rounded-zero-percent case.
            fixture=read(target)
            for step in fixture.get('steps',[]):
                vitals=step.get('state',{}).get('vitals',{})
                vitals.pop('absolute_health_known',None);vitals.pop('alive',None)
            target.write_text(json.dumps(fixture))

        args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),(str(workspace/'Client/DAoCBridgeClient.uproject') if installed else build['project']),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly',
              '-'+flag+'='+str(target),'-DaocBridgeCatalog='+str(workspace/'models.json'),'-DaocBridgeEquipmentCatalog='+str(workspace/'equipment_catalog_v01.json'),
              '-DaocBridgeKeyConfiguration='+str(output/'keys.ini'),'-DaocBridgeControlsSettings='+str(output/'camera.json'),'-nullrhi','-nosound','-unattended','-nosplash','-abslog='+str(output/(name+'_engine.log'))]
        with (output/(name+'_stdout.log')).open('w',encoding='utf-8') as log:result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=110,creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode==0,(name,str(output))
        report=read(Path(str(target)+'.native.json'));assert report['passed'] and not report.get('failures'),report
        reports[name]=report;print(json.dumps({name:report.get('checks')}),flush=True)
    assert digest(normal)==before
    proof=dict(passed=True,installed_client=installed,reports=reports,input_hashes=inputs,build_receipt_sha256=digest(bp),normal_installation_modified=False,server_started=False)
    (output/'verified.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    return dict(passed=True,checks={n:r['checks'] for n,r in reports.items()},output=str(output))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve())))
