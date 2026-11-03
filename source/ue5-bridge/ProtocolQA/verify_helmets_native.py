"""Verify the original Hibernian helmet library in a private Unreal host/client."""
import argparse,json,subprocess,time
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bridge-root',type=Path,required=True)
    parser.add_argument('--editor',type=Path,required=True)
    parser.add_argument('--installed',action='store_true')
    parser.add_argument('--capture',action='store_true')
    parser.add_argument('--figure',default='1984')
    parser.add_argument('--model',default='438')
    args=parser.parse_args();root=args.bridge_root.resolve();out=root/'Reports/helmets';out.mkdir(exist_ok=True)
    project=root/('Client/DAoCBridgeClient.uproject' if args.installed else 'GMCombatTest/NativeHost/BridgeGmHost.uproject')
    catalog=root/('equipment_catalog_v01.json' if args.installed else 'equipment_catalog_helmets_candidate.json')
    helmets=json.loads(catalog.read_text(encoding='utf-8-sig'))['armour']['helmets']
    assert len(helmets)==10 and sum(len(rows) for rows in helmets.values())==540,'Incomplete helmet catalogue'
    label=('installed_' if args.installed else 'candidate_')+(args.figure+'_'+args.model if args.capture else 'all')
    result_path=out/(label+'.json');engine_log=out/(label+'_engine.log');started=time.time()
    cmd=[str(args.editor),str(project),'/Engine/Maps/Entry','-game','-DaocBridge',
         '-DaocBridgeCatalog='+str(root/'models.json'),'-DaocBridgeEquipmentCatalog='+str(catalog),
         '-DaocBridgeArmourTest='+str(result_path),'-unattended','-nosound','-nosplash','-abslog='+str(engine_log)]
    if args.capture:
        assert args.model in helmets[args.figure]
        cmd+=['-d3d11','-RenderOffscreen','-DaocBridgeArmourCapture='+str(out/(label+'.png')),
              '-DaocBridgeArmourCaptureFigure='+args.figure,'-DaocBridgeArmourCaptureHelmet='+args.model]
    else:cmd+=['-nullrhi']
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:
        process=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
    assert process.returncode==0 and result_path.exists() and result_path.stat().st_mtime>=started
    report=json.loads(result_path.read_text(encoding='utf-8-sig'))
    assert report['checks']>=2462,'Native binary did not exercise the complete helmet library'
    if args.capture:assert 'Failed to compile Material' not in engine_log.read_text(encoding='utf-8-sig'),'Rendered material fallback'
    print(json.dumps(report));assert report['passed']

if __name__=='__main__':main()
