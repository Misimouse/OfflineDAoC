"""Render the original creation/customization UI with joint expansion choices."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def run(lab, engine):
    lab,engine=lab.resolve(),engine.resolve()
    assert lab.name=='ExpansionRaceLab'
    out=lab/'CombinedExpansionLobbyAcceptance'
    review=lab/'MinotaurOwnerReview'
    inputs=[out/'fixture.json']+[review/name for name in ['models.json','equipment_catalog.json','appearance_catalog.json']]
    inputs+=list((lab/'SharLobbyHost/Plugins/DAoCVisualBridge/Binaries/Win64').glob('*.dll'))
    assert any(p.suffix=='.dll' for p in inputs)
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    hashes={str(p):digest(p) for p in inputs}
    (out/'inputs.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    summary={}
    for screen in ['create','customize']:
        folder=out/screen;folder.mkdir(exist_ok=True)
        fixture=folder/'fixture.json';shutil.copy2(out/'fixture.json',fixture)
        command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(lab/'SharLobbyHost/SharLobbyHost.uproject'),
                 '/Engine/Maps/Entry','-game','-EnablePlugins=DAoCVisualBridge','-DaocBridge',
                 '-DaocBridgeCatalog='+str(review/'models.json'),'-DaocBridgeEquipmentCatalog='+str(review/'equipment_catalog.json'),
                 '-DaocBridgeLobbyAppearance='+str(review/'appearance_catalog.json'),'-DaocBridgeLobbyLore='+str(lab/'Delivery/lore.json'),
                 '-DaocBridgeCharacterLobbyTest='+str(fixture),'-DaocBridgeCharacterLobbyCapture='+str(folder/'screen.png'),
                 '-DaocBridgeCharacterLobbyScreen='+screen,'-unattended','-nosound','-nosplash','-d3d11','-RenderOffscreen',
                 '-windowed','-ForceRes','-ResX=1600','-ResY=900','-abslog='+str(folder/'engine.log')]
        with (folder/'stdout.log').open('w',encoding='utf-8') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
        raw=Path(str(fixture)+'.native.json').read_bytes()
        report=json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
        summary[screen]={'exit':result.returncode,**report}
        (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        print(screen,result.returncode,report.get('checks'),report.get('failures'),flush=True)
        assert result.returncode==0 and report['passed'] and not report['failures']
        assert all(report[k] for k in ['minotaur_creation_tested','shar_creation_tested','shar_vampiir_creation_tested'])
    assert hashes=={str(p):digest(p) for p in inputs},'Acceptance inputs changed during rendering'
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lab',type=Path,required=True)
    parser.add_argument('--engine',type=Path,required=True)
    args=parser.parse_args();run(args.lab,args.engine)
