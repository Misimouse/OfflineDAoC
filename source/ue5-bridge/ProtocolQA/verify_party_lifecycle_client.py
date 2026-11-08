"""Verify existing group state and native widgets without changing installed code."""
import argparse,json,os,shutil,subprocess
from datetime import datetime
from pathlib import Path
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest

def verify(workspace,install,engine):
    assert verify_files(workspace)['player_vitals_installed']
    source=Path(__file__).resolve().parents[1]
    root=workspace/'PartyLifecycleLab/Client'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    project=root/'Godot';project.mkdir(parents=True);(root/'Reports/group').mkdir(parents=True)
    (project/'project.godot').write_text('[application]\nconfig/name="Private Party QA"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    inputs={}
    for name in ['party_state.gd','interaction_state.gd','test_party_state.gd']:
        p=source/'Godot'/name;inputs[str(p)]=digest(p);shutil.copy2(p,project/name)
    (root/'Reports/ui_integration').mkdir(parents=True);seed=workspace/'Reports/ui_integration/fixture.json';shutil.copy2(seed,root/'Reports/ui_integration/fixture.json');inputs[str(seed)]=digest(seed)
    env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    exe=install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'
    r=subprocess.run([str(exe),'--headless','--path',str(project),'--script','res://test_party_state.gd'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    (root/'godot.log').write_text(r.stdout);assert r.returncode==0 and 'ERROR:' not in r.stdout,r.stdout
    state=json.loads((root/'Reports/group/godot_tests.json').read_text());assert state['passed'] and state['checks']>=30
    fixture=root/'fixture.json';group=json.loads((root/'Reports/group/fixture.json').read_text());group['classic_ui']['character']='IsolatedParty'+datetime.now().strftime('%Y%m%d%H%M%S');fixture.write_text(json.dumps(group),encoding='utf-8');assert group['party_fixture']
    receipt=workspace/'PlayerVitalsLab/installed.json';inputs[str(receipt)]=digest(receipt)
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(workspace/'Client/DAoCBridgeClient.uproject'),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeClassicTest='+str(fixture),'-DaocBridgeCatalog='+str(workspace/'models.json'),'-DaocBridgeInterfaceSettings='+str(root/'interface.ini'),'-DaocBridgeDisplaySettings='+str(root/'display.ini'),'-DaocBridgeKeyConfiguration='+str(root/'keys.ini'),'-DaocBridgeAudioSettings='+str(root/'audio.ini'),'-nullrhi','-unattended','-nosound','-nosplash','-abslog='+str(root/'engine.log')]
    with (root/'stdout.log').open('w') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    native_path=Path(str(fixture)+'.native.json');assert r.returncode==0 and native_path.exists(),str(root)
    native=json.loads(native_path.read_text(encoding='utf-8-sig'));assert native['passed'] and not native['failures'],native
    assert all(digest(Path(p))==sha for p,sha in inputs.items());verify_files(workspace)
    report=dict(passed=True,state_checks=state['checks'],native_checks=native['checks'],source_inputs=inputs,normal_installation_modified=False,server_started=False)
    (root/'verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return dict(passed=True,state_checks=state['checks'],native_checks=native['checks'],output=str(root))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['workspace','install','engine']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve(),a.engine.resolve())))
