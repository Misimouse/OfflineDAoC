"""Exercise fixed-world original siege impacts inside a private Unreal host."""
import argparse,json,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest

def verify(workspace,engine,installed=False):
    root=workspace/'SiegeImpactLab';build=json.loads((root/'native_build.json').read_text());assert build['passed']
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(normal)==(build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256'])
    out=root/('InstalledNativeAcceptance' if installed else 'NativeAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    reports=[]
    for mode,extra in [('impact',['-DaocBridgeSiegeImpactTest']),('weapon',['-DaocBridgeWeaponVisualTest'])]:
        report=out/(mode+'.json')
        args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(workspace/'Client/DAoCBridgeClient.uproject') if installed else build['project'],'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeCatalog='+str(workspace/'models.json'),'-DaocBridgeEquipmentCatalog='+str(workspace/'equipment_catalog_v01.json'),'-DaocBridgeSpellVisualAcceptance='+str(report),'-nosound','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(out/(mode+'.log'))]+extra
        for key,name in [('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:args.append('-DaocBridge'+key+'='+str(out/name))
        with (out/(mode+'_stdout.log')).open('w',encoding='utf-8') as log:result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode==0 and report.exists(),str(out)
        data=json.loads(report.read_text(encoding='utf-8-sig'));assert data['passed'],data
        reports.append(dict(mode=mode,checks=data['checks'],report=str(report),sha256=digest(report)))
    assert digest(normal)==(build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256'])
    receipt=dict(passed=True,normal_installation_modified=False,real_server=False,installed_client=installed,reports=reports,build_sha256=digest(root/'native_build.json'))
    (out/'verified.json').write_text(json.dumps(receipt,indent=2));(root/('installed_native_acceptance.json' if installed else 'native_acceptance.json')).write_text(json.dumps(dict(passed=True,proof=str(out/'verified.json'),proof_sha256=digest(out/'verified.json')),indent=2))
    return dict(passed=True,reports=reports,output=str(out))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--installed',action='store_true');a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.installed)))
