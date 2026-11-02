from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time
from pathlib import Path
R=Path(str(ROOT))
D=R/'Reports/release_camera/native';D.mkdir(exist_ok=True)
project=R/'GMCombatTest/NativeHost/BridgeGmHost.uproject'
tests=[('combat','DaocBridgeCombatVisualTest',R/'Reports/combat_visual/fixture.json',True),('gm','DaocBridgePlayerStateTest',R/'Reports/player_release/native_fixture.json',True),('pose','DaocBridgePoseTest',D/'pose.json',False),('equipment','DaocBridgeEquipmentTest',R/'Reports/equipment/fixture.json',True)]
results={}
for name,flag,fixture,suffix in tests:
    start=time.time();output=Path(str(fixture)+'.native.json') if suffix else fixture
    cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeCatalog='+str(R/('models_combat_samples.json' if name=='pose' else 'models.json')),'-DaocBridgeEquipmentCatalog='+str(R/'equipment_catalog_v01.json'),'-'+flag+'='+str(fixture),'-nullrhi','-unattended','-nosound','-nosplash']
    with (D/(name+'.log')).open('w',encoding='utf-8') as log:
        p=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    assert p.returncode==0 and output.exists() and output.stat().st_mtime>=start,(name,p.returncode)
    data=json.loads(output.read_text(encoding='utf-8-sig'));results[name]=data
    print(name,json.dumps(data),flush=True)
    assert data['passed'],name
(D/'acceptance.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
