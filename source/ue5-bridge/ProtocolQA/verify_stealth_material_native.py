"""Check per-avatar hidden material lifetime in the private native candidate."""
import argparse,json,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,engine,materials):
    build_path=workspace/'StealthLab/native_build.json';build=json.loads(build_path.read_text());assert build['passed']
    source=Path(__file__).resolve().parents[1]/'UnrealPlugin/DAoCVisualBridge/Source'
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    prepared=json.loads(materials.read_text());assert prepared['passed'] and prepared['originals_unchanged'] and not prepared['installed'] and not prepared.get('diagnostic_only')
    assert len(prepared['materials'])>=40
    normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(normal)==build['normal_binary_sha256']
    project=Path(build['project']);binary=project.parent/'Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(binary)==build['binaries_sha256'][binary.name]
    out=workspace/'StealthLab/MaterialAcceptance'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    audit_path=workspace/'StealthLab/MaterialAudit/verified.json';audit=json.loads(audit_path.read_text());assert audit['passed']
    samples={r['material'] for rows in audit['samples'].values() for r in rows}
    samples.update(p for p,v in prepared['originals'].items() if 'blend' in v)
    for mode in {v['effective_blend'] for v in prepared['originals'].values()}:
        samples.add(next(p for p,v in prepared['originals'].items() if v['effective_blend']==mode))
    assert samples.issubset(prepared['materials'])
    fixture=out/'fixture.json';fixture.write_text(json.dumps(dict(prepared,acceptance_materials=sorted(samples))),encoding='utf-8')
    inputs={str(p):digest(p) for p in [materials,build_path,binary,normal,fixture,audit_path]}
    content=workspace/'Client/Plugins/DAoCVisualBridge/Content'
    for asset in prepared['materials'].values():
        assert asset.startswith('/DAoCVisualBridge/Stealth_v01/')
        file=content/(asset.split('.')[0].removeprefix('/DAoCVisualBridge/')+'.uasset');inputs[str(file)]=digest(file)
    report=out/'native.json'
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeStealthMaterialTest='+str(report),'-DaocBridgeStealthMaterials='+str(fixture),'-nullrhi','-unattended','-nosound','-nosplash','-abslog='+str(out/'engine.log')]
    with (out/'stdout.log').open('w',encoding='utf-8') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0 and report.exists(),str(out)
    result=json.loads(report.read_text(encoding='utf-8-sig'));assert result['passed'] and not result['failures'] and result['checks']>=400,result
    assert all(digest(Path(p))==h for p,h in inputs.items())
    assert all(digest(source/p)==h for p,h in build['source_sha256'].items())
    result.update(source_inputs=inputs,rendered=False,owner_gameplay_accepted=False,runtime_material_samples=len(samples),prepared_materials=len(prepared['materials']))
    (out/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return dict(passed=True,checks=result['checks'],rendered=False,output=str(out))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['workspace','engine','materials']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.materials.resolve())))
