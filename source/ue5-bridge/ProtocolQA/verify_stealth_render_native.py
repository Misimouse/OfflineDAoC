"""Render visible/hidden/revealed copies of a captured original character privately."""
import argparse,json,subprocess,struct,zlib
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def png_rgb(path):
    """Read non-interlaced 8/16-bit RGB/RGBA engine captures without extra packages."""
    data=path.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
    at=8;compressed=bytearray();size=None
    while at<len(data):
        length=struct.unpack('>I',data[at:at+4])[0];kind=data[at+4:at+8];chunk=data[at+8:at+8+length];at+=length+12
        if kind==b'IHDR':
            w,h,depth,colour,compression,filtering,interlace=struct.unpack('>IIBBBBB',chunk)
            assert depth in [8,16] and colour in [2,6] and compression==filtering==interlace==0
            size=(w,h);channels=3 if colour==2 else 4;sample_bytes=depth//8;bpp=channels*sample_bytes
        elif kind==b'IDAT':compressed.extend(chunk)
        elif kind==b'IEND':break
    assert size
    raw=zlib.decompress(compressed);stride=w*bpp;previous=bytearray(stride);pixels=bytearray();at=0
    for _ in range(h):
        kind=raw[at];row=bytearray(raw[at+1:at+stride+1]);at+=stride+1;assert kind<=4
        for i in range(stride):
            a=row[i-bpp] if i>=bpp else 0;b=previous[i];c=previous[i-bpp] if i>=bpp else 0
            if kind==1:predict=a
            elif kind==2:predict=b
            elif kind==3:predict=(a+b)//2
            elif kind==4:
                p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c);predict=a if pa<=pb and pa<=pc else b if pb<=pc else c
            else:predict=0
            row[i]=(row[i]+predict)&255
        if channels==3 and sample_bytes==1:pixels.extend(row)
        else:
            for i in range(0,stride,bpp):pixels.extend([row[i],row[i+sample_bytes],row[i+2*sample_bytes]])
        previous=row
    assert at==len(raw)
    return size,pixels

def verify(workspace,engine,materials,installed=False):
    build_path=workspace/'StealthLab/native_build.json';build=json.loads(build_path.read_text());assert build['passed']
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    prepared=json.loads(materials.read_text());assert prepared['passed'] and prepared['originals_unchanged'] and not prepared['installed'] and not prepared.get('diagnostic_only')
    proof=next(p for p in reversed(sorted((workspace/'StealthLab/RealProtocol').glob('*/verified.json'))) if json.loads(p.read_text()).get('passed') and len(json.loads(p.read_text()).get('checks',{}))>=16)
    original=proof.parent/'active_snapshot.json';snapshot=json.loads(original.read_text());assert snapshot['player_status']['ready'] and snapshot['player_status']['vitals']['alive']
    row=next(r for r in snapshot['entities'] if r['id']=='player:local');assert row['look'] and row['stealth_render_known'] and not row['stealth_render_hidden']
    project=Path(build['project']);binary=project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(binary)==build['binaries_sha256'][binary.name]
    expected_normal=build['binaries_sha256'][binary.name] if installed else build['normal_binary_sha256']
    assert digest(normal)==expected_normal
    if installed:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)['stealth_installed']
        assert materials.resolve()==(workspace/'Client/Plugins/DAoCVisualBridge/Content/ClassicUI/stealth_materials.json').resolve()
        project=workspace/'Client/DAoCBridgeClient.uproject'
    out=workspace/('StealthLab/InstalledRenderedAcceptance' if installed else 'StealthLab/RenderedAcceptance')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    models=workspace/'models.json';equipment=workspace/'equipment_catalog_v01.json'
    inputs={str(p):digest(p) for p in [materials,original,proof,models,equipment,build_path,binary,normal]}
    report=out/'native.json'
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeStealthMaterialTest='+str(report),'-DaocBridgeStealthMaterials='+str(materials),'-DaocBridgeStealthFixture='+str(original),'-DaocBridgeStealthCapture='+str(out),'-DaocBridgeCatalog='+str(models),'-DaocBridgeEquipmentCatalog='+str(equipment)]
    for key,name in [('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:args.append('-DaocBridge'+key+'='+str(out/name))
    args+=['-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-unattended','-nosound','-nosplash','-abslog='+str(out/'engine.log')]
    with (out/'stdout.log').open('w',encoding='utf-8') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=360,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0 and report.exists(),str(out)
    result=json.loads(report.read_text(encoding='utf-8-sig'));assert result['passed'] and not result['failures'] and result['rendered'],result
    images={name:png_rgb(out/(name+'.png')) for name in ['visible','hidden','revealed','background']}
    assert all(size==(768,1024) for size,pixels in images.values()),'Invalid render dimensions'
    assert all(max(images[n][1])-min(images[n][1])>30 for n in ['visible','hidden','revealed']),'Blank figure render'
    visible=images['visible'][1]
    hidden_difference=sum(abs(a-b) for a,b in zip(visible,images['hidden'][1]))/len(visible)
    restoration_error=sum(abs(a-b) for a,b in zip(visible,images['revealed'][1]))/len(visible)
    background=images['background'][1]
    visible_signal=sum(abs(a-b) for a,b in zip(visible,background))/len(visible)
    hidden_signal=sum(abs(a-b) for a,b in zip(images['hidden'][1],background))/len(visible)
    silhouette_ratio=hidden_signal/max(visible_signal,1e-9)
    result['pixel_measurements']={'hidden_mean_difference':hidden_difference,'restoration_mean_error':restoration_error,'visible_signal':visible_signal,'hidden_signal':hidden_signal,'hidden_silhouette_ratio':silhouette_ratio}
    (out/'pixel_measurements.json').write_text(json.dumps(result['pixel_measurements'],indent=2),encoding='utf-8')
    assert hidden_difference>1 and restoration_error<1 and visible_signal>1 and .05<silhouette_ratio<1.1,result['pixel_measurements']
    assert all(digest(Path(p))==h for p,h in inputs.items())
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    result.update(source_inputs=inputs,owner_gameplay_accepted=False,normal_runtime_modified=False,pixel_checks=3,installed_binary_verified=installed)
    (out/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return dict(passed=True,native_checks=result['checks'],pixel_checks=3,output=str(out))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['workspace','engine','materials']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--installed',action='store_true')
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.materials.resolve(),a.installed)))
