"""Verify existing inventory and merchant state and native widgets without changing installed code."""
import argparse,json,os,shutil,subprocess
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest

def verify(workspace,install,engine):
    assert verify_files(workspace)['compass_installed']
    source=Path(__file__).resolve().parents[1]
    root=workspace/'MerchantLifecycleLab/Client'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    project=root/'Godot';project.mkdir(parents=True)
    (project/'project.godot').write_text('[application]\nconfig/name="Private Merchant QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    inputs={}
    for p in (source/'Godot').glob('*.gd'):
        inputs[str(p)]=digest(p);shutil.copy2(p,project/p.name)
    for name in ['ui_integration','inventory','inventory_rejection']:(root/'Reports'/name).mkdir(parents=True,exist_ok=True)
    seed=workspace/'Reports/ui_integration/fixture.json';shutil.copy2(seed,root/'Reports/ui_integration/fixture.json');inputs[str(seed)]=digest(seed)
    catalog=workspace/'models.json';shutil.copy2(catalog,root/'models.json');inputs[str(catalog)]=digest(catalog)
    env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    exe=install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'
    states={}
    for script,folder in [('test_inventory','inventory'),('test_inventory_denial','inventory_rejection')]:
        r=subprocess.run([str(exe),'--headless','--path',str(project),'--script','res://'+script+'.gd'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
        (root/(script+'.log')).write_text(r.stdout,encoding='utf-8');assert r.returncode==0 and 'ERROR:' not in r.stdout,r.stdout
        state=json.loads((root/'Reports'/folder/'godot_tests.json').read_text(encoding='utf-8'));assert state['passed'] and not state['failures']
        states[script]=state['checks']
    state=dict(checks=sum(states.values()));assert states=={'test_inventory':35,'test_inventory_denial':23}
    fixture=root/'fixture.json';group=json.loads((root/'Reports/inventory/fixture.json').read_text());fixture.write_text(json.dumps(group),encoding='utf-8')
    receipt=workspace/'CompassLab/installed.json';inputs[str(receipt)]=digest(receipt)
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(workspace/'Client/DAoCBridgeClient.uproject'),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeInventoryTest='+str(fixture),'-DaocBridgeCatalog='+str(workspace/'models.json'),'-DaocBridgeInterfaceSettings='+str(root/'interface.ini'),'-DaocBridgeDisplaySettings='+str(root/'display.ini'),'-DaocBridgeKeyConfiguration='+str(root/'keys.ini'),'-DaocBridgeAudioSettings='+str(root/'audio.ini'),'-nullrhi','-unattended','-nosound','-nosplash','-abslog='+str(root/'engine.log')]
    with (root/'stdout.log').open('w',encoding='utf-8') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    native_path=Path(str(fixture)+'.native.json');assert r.returncode==0 and native_path.exists(),str(root)
    native=json.loads(native_path.read_text(encoding='utf-8-sig'));assert native['passed'] and not native['failures'] and native['checks']>=27,native
    assert all(digest(Path(p))==sha for p,sha in inputs.items());verify_files(workspace)
    report=dict(passed=True,state_checks=state['checks'],state_suites=states,native_checks=native['checks'],source_inputs=inputs,normal_installation_modified=False,server_started=False)
    (root/'verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return dict(passed=True,state_checks=state['checks'],state_suites=states,native_checks=native['checks'],output=str(root))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['workspace','install','engine']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve())))
