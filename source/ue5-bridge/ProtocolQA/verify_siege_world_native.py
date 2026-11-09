"""Render original siege bodies and evaluate their original animation assets in native UE5."""
import argparse,json,subprocess
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest

def verify(workspace,engine,installed=False):
 root=workspace/'SiegeWorldLab';bp=root/'native_build.json';build=json.loads(bp.read_text());assert build['passed']
 normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';assert digest(normal)==(build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256'])
 source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source';assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
 imported=json.loads((root/'asset_import.json').read_text());assert imported['passed'] and len(imported['models'])==10 and all(r['bounds_max_error_cm']<.2 for r in imported['models'].values())
 assert all(digest(Path(p))==h for p,h in imported['files'].items())
 out=root/('InstalledNativeAcceptance' if installed else 'NativeAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True);report=out/'siege_world.json'
 project=workspace/'Client/DAoCBridgeClient.uproject' if installed else Path(build['project']);catalog=workspace/'models.json' if installed else root/'models_candidate.json'
 args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeCatalog='+str(catalog),'-DaocBridgeEquipmentCatalog='+str(workspace/'equipment_catalog_v01.json'),'-DaocBridgeSiegeWorldTest='+str(report),'-nosound','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(out/'engine.log')]
 for key,name in [('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:args.append('-DaocBridge'+key+'='+str(out/name))
 with (out/'stdout.log').open('w',encoding='utf-8') as log:result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=480,creationflags=subprocess.CREATE_NO_WINDOW)
 assert result.returncode==0 and report.exists(),str(out)
 data=json.loads(report.read_text(encoding='utf-8-sig'));assert data['passed'] and data['checks']>=110 and len(data['captures'])==10 and not data['server_started'],data
 assert digest(normal)==(build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256'])
 data.update(build_receipt_sha256=digest(bp),asset_import_sha256=digest(root/'asset_import.json'),catalog_sha256=digest(catalog),normal_installation_modified=False,installed_client=installed)
 for capture in data['captures']:capture['image_sha256']=digest(Path(capture['image']))
 proof=out/'verified.json';proof.write_text(json.dumps(data,indent=2));(root/('installed_native_acceptance.json' if installed else 'native_acceptance.json')).write_text(json.dumps(dict(passed=True,proof=str(proof),proof_sha256=digest(proof)),indent=2))
 return dict(passed=True,checks=data['checks'],models=10,output=str(out))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--installed',action='store_true');a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.installed)))
