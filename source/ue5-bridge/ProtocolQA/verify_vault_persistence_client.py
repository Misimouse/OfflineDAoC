"""Verify existing vault state and native widgets without changing installed code."""
import argparse,json,os,shutil,subprocess
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest

def verify(workspace,install,engine,quantity_candidate=False,candidate_lab="InventoryQuantityLab"):
    assert candidate_lab in ["InventoryQuantityLab","RvRWindowsLab","SiegeWindowLab","GroundTargetLab"]
    assert verify_files(workspace)['hover_details_installed']
    source=Path(__file__).resolve().parents[1]
    root=workspace/(candidate_lab+'/VaultRegression' if quantity_candidate else 'VaultPersistenceLab/Client')/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    project=root/'Godot';project.mkdir(parents=True);(root/'Reports/vault').mkdir(parents=True)
    (project/'project.godot').write_text('[application]\nconfig/name="Private Vault QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    inputs={}
    for name in ['vault_state.gd','inventory_state.gd','interaction_state.gd','classic_ui_state.gd','test_vault_state.gd']:
        p=source/'Godot'/name;inputs[str(p)]=digest(p);shutil.copy2(p,project/name)
    env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    exe=install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'
    r=subprocess.run([str(exe),'--headless','--path',str(project),'--script','res://test_vault_state.gd'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    (root/'godot.log').write_text(r.stdout);assert r.returncode==0 and 'ERROR:' not in r.stdout,r.stdout
    state=json.loads((root/'Reports/vault/godot_tests.json').read_text());assert state['passed'] and state['checks']>=25
    fixture=root/'fixture.json';shutil.copy2(workspace/'Reports/vault/fixture.json',fixture);inputs[str(workspace/'Reports/vault/fixture.json')]=digest(fixture)
    receipt=workspace/'HoverDetailsLab/installed.json';inputs[str(receipt)]=digest(receipt)
    build_path=workspace/candidate_lab/'native_build.json'
    build=json.loads(build_path.read_text()) if quantity_candidate else None
    native_project=Path(build['project']) if build else workspace/'Client/DAoCBridgeClient.uproject'
    if build:assert build['passed'] and all(digest(source/'UnrealPlugin/DAoCVisualBridge/Source'/p)==h for p,h in build['source_sha256'].items())
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(native_project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeClassicTest='+str(fixture),'-DaocBridgeCatalog='+str(workspace/'models.json'),'-DaocBridgeDisplaySettings='+str(root/'display.ini'),'-DaocBridgeKeyConfiguration='+str(root/'keys.ini'),'-DaocBridgeAudioSettings='+str(root/'audio.ini'),'-nullrhi','-unattended','-nosound','-nosplash','-abslog='+str(root/'engine.log')]
    with (root/'stdout.log').open('w') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    native_path=Path(str(fixture)+'.native.json');assert r.returncode==0 and native_path.exists(),str(root)
    native=json.loads(native_path.read_text(encoding='utf-8-sig'));assert native['passed'] and not native['failures'],native
    assert all(digest(Path(p))==sha for p,sha in inputs.items());verify_files(workspace)
    report=dict(passed=True,state_checks=state['checks'],native_checks=native['checks'],source_inputs=inputs,normal_installation_modified=False,server_started=False)
    if build:report['build_receipt_sha256']=digest(build_path)
    (root/'verified.json').write_text(json.dumps(report,indent=2));return dict(passed=True,state_checks=state['checks'],native_checks=native['checks'],output=str(root))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['workspace','install','engine']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve())))
