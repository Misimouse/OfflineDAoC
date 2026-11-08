"""Validate native water sampling against all original Godot mask cells."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
from prepare_combined_expansion_data import digest
from verify_options_audio_native import read

def verify(workspace,engine,lab_name="WaterMovementLab"):
    assert lab_name in ["WaterMovementLab","LiveRidingLab","KeyConfigurationLab","InterfaceKeysLab","DisplaySettingsLab","DisplaySettingsFixLab","GuildWindowLab","EmblemWindowLab","ItemHandoverLab","HoverDetailsLab","UIScaleLab"]
    root=workspace/lab_name;build=read(root/'native_build.json');resources=read(workspace/'WaterMovementLab/resources.json')
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert build['passed'] and resources['passed'] and digest(normal)==build['normal_binary_sha256']
    reference_path=sorted((workspace/'WaterMovementLab/OriginalField').glob('*/verified.json'))[-1];reference=read(reference_path)
    assert reference['passed'] and reference['matched_cells']==65536
    catalog=Path(resources['catalog']);assert digest(catalog)==resources['catalog_sha256']
    assert all(digest(Path(p))==sha for p,sha in resources['input_hashes'].items())
    data=read(catalog);mask=bytes(body for body,length in data['mask_runs'] for _ in range(length))
    output=root/'DataAcceptance'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');output.mkdir(parents=True)
    target=output/'water.json'
    command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),build['project'],'/Engine/Maps/Entry','-game','-EnablePlugins=DAoCVisualBridge','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeWaterDataTest='+str(target),'-DaocBridgeWaterField='+str(catalog),'-DaocBridgeCatalog='+str(workspace/'models.json'),'-unattended','-nosplash','-nosound','-nullrhi','-abslog='+str(output/'engine.log')]
    with (output/'stdout.log').open('w',encoding='utf-8') as log:process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
    assert process.returncode==0 and target.exists(),str(output)
    report=read(target);assert report['passed'] and not report['failures'] and report['checks']>=65550 and report['wet_cells']==6785,report
    assert report['mask_sha1']==hashlib.sha1(mask).hexdigest()
    assert digest(normal)==build['normal_binary_sha256'] and not report['movement_implemented'] and not report['visuals_modified']
    report.update(build_receipt_sha256=digest(root/'native_build.json'),resources_receipt_sha256=digest(workspace/'WaterMovementLab/resources.json'),original_field_receipt_sha256=digest(reference_path),normal_installation_modified=False,server_started=False)
    (output/'verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return {'passed':True,'checks':report['checks'],'matched_cells':65536,'wet_cells':6785,'output':str(output),'movement_implemented':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','engine']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(verify(args.workspace.resolve(),args.engine.resolve())))
