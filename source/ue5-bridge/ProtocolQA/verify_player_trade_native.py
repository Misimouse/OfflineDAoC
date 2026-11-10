"""Exercise original trade controls in a private rendered UE viewport; no server."""
import argparse,json,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,engine,accepted_ui_proof=None,lab_name="PlayerTradeUILab",installed=False):
    assert lab_name in ['PlayerTradeUILab','PlayerTradeGatewayLab']
    root=workspace/lab_name;receipt=root/'native_build.json';build=json.loads(receipt.read_text());assert build['passed']
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==sha for p,sha in build['source_sha256'].items())
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    expected=build['binaries_sha256'][normal.name] if installed else build['normal_binary_sha256']
    if installed:
        from player_trade_receipts import verify as verify_installed
        assert verify_installed(workspace)[0]['installed']
    assert digest(normal)==expected
    content=json.loads((workspace/'PlayerTradeUILab/content_verified.json').read_text());assert digest(Path(content['candidate_art']))==digest(Path(content['source_art']))==content['sha256']
    out=root/('InstalledAcceptance' if installed else 'NativeAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True);fixture=out/'trade.json'
    own=dict(slot=40,name='Training shield',model=59,icon=912,token='own-cloak',count=12)
    offer=dict(title='Trading with Friend',own_slots=[40]+[0]*9,own_money=[0,0,0,1,25],partner_money=[0,0,0,0,50],partner_items=[dict(slot=63,name='Partner shield',model=59,icon=912)])
    trade=dict(visible=True,pending=False,token='offer-one',partner_id='player:30',offer=offer)
    inventory=dict(ready=True,pending=False,state_revision=7,items=[own])
    fixture.write_text(json.dumps(dict(inventory=inventory,trade=trade),indent=2))
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),build['project'],'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgePlayerTradeTest='+str(fixture),'-nosound','-unattended','-nosplash','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-abslog='+str(out/'engine.log')]
    if installed:args[1]=str(workspace/'Client/DAoCBridgeClient.uproject')
    for key,name in [('DisplaySettings','display.ini'),('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:args.append('-DaocBridge'+key+'='+str(out/name))
    if accepted_ui_proof:
        assert accepted_ui_proof.resolve().is_relative_to((root/'NativeAcceptance').resolve())
        data=json.loads(accepted_ui_proof.read_text());assert data['passed'] and data['checks']>=28 and data['build_receipt_sha256']==digest(receipt)
        screenshot=data['screenshot']
    else:
        with (out/'stdout.log').open('w',encoding='utf-8') as log:run=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        report=Path(str(fixture)+'.native.json');assert run.returncode==0 and report.exists(),str(out)
        data=json.loads(report.read_text(encoding='utf-8-sig'));assert data['passed'] and not data['failures'] and data['checks']>=28,data
        screenshot=str(fixture)+'.png'
    assert digest(normal)==expected and all(digest(source/p)==sha for p,sha in build['source_sha256'].items())
    original=workspace/'Reports/exchange/fixture.json';regression=out/'exchange.json'
    original_data=json.loads(original.read_text(encoding='utf-8-sig'));assert all(k in original_data for k in ['inventory','player_status','classic_ui','exchange','listings'])
    regression.write_bytes(original.read_bytes())
    more=[v.replace('-DaocBridgePlayerTradeTest='+str(fixture),'-DaocBridgeExchangeTest='+str(regression)).replace('-abslog='+str(out/'engine.log'),'-abslog='+str(out/'exchange_engine.log')) for v in args]
    with (out/'exchange_stdout.log').open('w',encoding='utf-8') as log:old=subprocess.run(more,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    old_report=Path(str(regression)+'.native.json');assert old.returncode==0 and old_report.exists(),str(out)
    old_data=json.loads(old_report.read_text(encoding='utf-8-sig'));assert old_data['passed'] and not old_data['failures'],old_data
    assert digest(normal)==expected
    data['exchange_regression_checks']=old_data['checks'];data['exchange_regression_proof']=str(old_report)
    data.update(build_receipt_sha256=digest(receipt),normal_installation_modified=False,screenshot=screenshot,installed=installed)
    proof=out/'verified.json';proof.write_text(json.dumps(data,indent=2));return dict(passed=True,checks=data['checks'],proof=str(proof),screenshot=data['screenshot'])
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','engine']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--accepted-ui-proof',type=Path)
    p.add_argument('--gateway',action='store_true')
    p.add_argument('--installed',action='store_true')
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.accepted_ui_proof,"PlayerTradeGatewayLab" if a.gateway else "PlayerTradeUILab",a.installed)))
