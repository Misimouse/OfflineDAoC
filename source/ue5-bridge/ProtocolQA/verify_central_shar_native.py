"""Render male/female Shar creation and customization with installed native assets."""
import argparse
import copy
from datetime import datetime
import json
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest


def read(p):
    raw=p.read_bytes();return json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))


def verify(workspace,engine):
    plan_path=workspace/'ExpansionRaceLab/CentralDelivery/SharActivation/plan.json';plan=read(plan_path)
    assert plan['passed'] and plan['only_race_enabled']==18 and not plan['installed']
    original=read(workspace/'ExpansionRaceLab/CombinedExpansionLobbyAcceptance/fixture.json')
    choices=original['character_lobby']['choices']
    assert len(choices)==95 and len([c for c in choices if c['race']=='Shar'])==12
    assert {c['class_id'] for c in choices if c['race']=='Shar'}==set(plan['admitted_classes'])
    assert all(18 in plan['rules']['classes'][str(c['class_id'])]['races'] for c in choices if c['race']=='Shar')
    plugin=workspace/'Client/Plugins/DAoCVisualBridge'
    inputs=[plan_path,workspace/'models.json',workspace/'equipment_catalog_v01.json',
        plugin/'Content/ClassicUI/Pregame/appearance_catalog.json',plugin/'Content/ClassicUI/Pregame/lore.json',
        plugin/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll']
    hashes={str(p):digest(p) for p in inputs}
    root=workspace/'Reports/central_shar_activation/native';root.mkdir(parents=True,exist_ok=True)
    assert not (root/'verified.json').exists(),'Preserve accepted native evidence'
    output=root/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir()
    cases={}
    for female in [False,True]:
        for screen in ['create','customize']:
            label=('female' if female else 'male')+'_'+screen;folder=output/label;folder.mkdir(exist_ok=True)
            fixture=copy.deepcopy(original);fixture.update(test_race='Shar',test_female=female,test_slot=1 if female else 2)
            path=folder/'fixture.json';path.write_text(json.dumps(fixture),encoding='utf-8')
            command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(workspace/'Client/DAoCBridgeClient.uproject'),'/Engine/Maps/Entry',
                '-game','-EnablePlugins=DAoCVisualBridge','-DaocBridge','-DaocBridgeReadOnly',
                '-DaocBridgeCatalog='+str(workspace/'models.json'),'-DaocBridgeEquipmentCatalog='+str(workspace/'equipment_catalog_v01.json'),
                '-DaocBridgeLobbyAppearance='+str(plugin/'Content/ClassicUI/Pregame/appearance_catalog.json'),
                '-DaocBridgeLobbyLore='+str(plugin/'Content/ClassicUI/Pregame/lore.json'),
                '-DaocBridgeCharacterLobbyTest='+str(path),'-DaocBridgeCharacterLobbyCapture='+str(folder/'screen.png'),
                '-DaocBridgeCharacterLobbyScreen='+screen,'-unattended','-nosound','-nosplash','-d3d11','-RenderOffscreen',
                '-windowed','-ForceRes','-ResX=1600','-ResY=900','-abslog='+str(folder/'engine.log')]
            with (folder/'stdout.log').open('w',encoding='utf-8') as log:
                process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=200,creationflags=subprocess.CREATE_NO_WINDOW)
            report=read(Path(str(path)+'.native.json'))
            assert process.returncode==0 and report['passed'] and not report['failures'],(label,report.get('failures'))
            assert report['shar_creation_tested'] and report['shar_vampiir_creation_tested'] and not report['live_account']
            assert report['preview_model']==(1087 if female else 1075)
            image=folder/'screen.png';assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') and image.stat().st_size>10000
            cases[label]={'checks':report['checks'],'model':report['preview_model'],'capture':str(image),'capture_sha256':digest(image)}
            print(label+' passed',flush=True)
    assert all(digest(Path(p))==sha for p,sha in hashes.items())
    result={'passed':True,'installed_native_inputs':True,'normal_installation_modified':False,'server_started':False,
        'inputs':hashes,'cases':cases,'owner_visual_acceptance':False}
    (output/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (root/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return {'passed':True,'cases':len(cases),'checks':sum(row['checks'] for row in cases.values())}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','engine']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(verify(args.workspace.resolve(),args.engine.resolve())))
