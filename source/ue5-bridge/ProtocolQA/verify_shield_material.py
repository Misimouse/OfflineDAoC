"""Exercise original shield UVs/emblems and reject rendered shader fallback.

The native parameter checks alone pass even when Unreal displays a checkerboard.
This runs D3D11 and also inspects the complete engine log for compilation errors.
No server/account is used. Run after repair_shield_material_unreal.py.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bridge-root',type=Path,required=True)
    parser.add_argument('--editor',type=Path,required=True)
    parser.add_argument('--installed',action='store_true')
    args=parser.parse_args()
    root=args.bridge_root.resolve()
    out=root/'Reports/shield_material'
    out.mkdir(parents=True,exist_ok=True)
    project=root/('Client/DAoCBridgeClient.uproject' if args.installed else 'GMCombatTest/NativeHost/BridgeGmHost.uproject')
    catalog=root/('equipment_catalog_v01.json' if args.installed else 'equipment_catalog_shield_candidate.json')
    stock=root/'Client/Plugins/DAoCVisualBridge/Content/Emblems_v01/M_OriginalShieldEmblem.uasset'
    guarded=[stock,root/'models.json',root/'equipment_catalog_v01.json']
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in guarded}
    label='installed' if args.installed else 'candidate'
    fixture=out/(label+'_fixture.json')
    shutil.copy2(root/'Reports/equipment/fixture.json',fixture)
    native=Path(str(fixture)+'.native.json')
    engine_log=out/(label+'_engine.log')
    started=time.time()
    cmd=[str(args.editor),str(project),'/Engine/Maps/Entry','-game','-DaocBridge',
         '-DaocBridgeCatalog='+str(root/'models.json'),'-DaocBridgeEquipmentCatalog='+str(catalog),
         '-DaocBridgeEquipmentTest='+str(fixture),'-DaocBridgeEmblemEquipmentTest',
         '-d3d11','-RenderOffscreen','-unattended','-nosound','-nosplash','-abslog='+str(engine_log)]
    try:
        with (out/(label+'_console.log')).open('w',encoding='utf-8') as log:
            result=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    finally:
        assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in guarded},'An original asset or active catalogue changed during verification'
    assert result.returncode==0 and native.exists() and native.stat().st_mtime>=started,'Native test did not complete'
    checks=json.loads(native.read_text(encoding='utf-8-sig'))
    errors=[line for line in engine_log.read_text(encoding='utf-8-sig').splitlines() if 'Failed to compile Material' in line or 'Missing Clamp input' in line]
    report={'passed':checks['passed'] and not errors,'checks':checks['checks'],
            'compiler_errors':errors,'original_asset_unchanged':True,'real_server':False,
            'material':json.loads(catalog.read_text(encoding='utf-8-sig'))['emblems']['material']}
    (out/(label+'_verification.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    assert report['passed'],report

if __name__=='__main__':main()
