"""Synthetic tampering tests for the narrowly scoped stealth installation receipt."""
import argparse,json,tempfile
from pathlib import Path
from central_activation_receipts import verify_stealth_successor,STEALTH_NATIVE_TARGETS,STEALTH_GODOT_TARGETS,STEALTH_NEW_NAMES
from prepare_combined_expansion_data import digest

def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')

def verify(workspace):
    root=workspace/'StealthLab/ReceiptTests';root.mkdir(parents=True,exist_ok=True);checks=0
    with tempfile.TemporaryDirectory(dir=root,prefix='synthetic_') as folder:
        w=Path(folder).resolve();assert w.is_relative_to(root.resolve())
        plugin=w/'Client/Plugins/DAoCVisualBridge';old_source={};old_binary={}
        for rel in STEALTH_NATIVE_TARGETS:
            if Path(rel).name in STEALTH_NEW_NAMES:continue
            p=plugin/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(('old '+rel).encode())
            if rel.startswith('Source/'):old_source[rel.removeprefix('Source/')]=digest(p)
            else:old_binary[p.name]=digest(p)
        prior_build=w/'WorldClockLab/native_build.json';put(prior_build,dict(source_sha256=old_source,binaries_sha256=old_binary))
        baseline={}
        for name in STEALTH_GODOT_TARGETS:
            if name in STEALTH_NEW_NAMES:continue
            p=w/'Godot'/name;p.parent.mkdir(exist_ok=True);p.write_text('old '+name);baseline[str(p)]=digest(p)
        before=w/'WorldClockLab/before.json';put(before,dict(passed=True,normal_runtime_unchanged=True,database_restored=True,source_inputs=baseline))
        gateway=w/'Godot/live_gateway.gd';old_gateway=digest(gateway);gateway.write_text('world clock gateway')
        clock=dict(native_after_sha256=old_binary['UnrealEditor-DAoCVisualBridge.dll'],godot_before_proof=str(before),
                   files=[dict(target=str(gateway),before_sha256=old_gateway,after_sha256=digest(gateway))],
                   evidence={str(prior_build):digest(prior_build),str(before):digest(before)})
        clock_path=w/'WorldClockLab/installed.json';put(clock_path,clock)
        rows=[];new_source={};new_binary={}
        for rel in STEALTH_NATIVE_TARGETS:
            p=plugin/rel;p.parent.mkdir(parents=True,exist_ok=True)
            previous=digest(p) if p.exists() else None;p.write_bytes(('stealth '+rel).encode())
            rows.append(dict(source=str(p),target=str(p),before_sha256=previous,after_sha256=digest(p)))
            if rel.startswith('Source/'):new_source[rel.removeprefix('Source/')]=digest(p)
            else:new_binary[p.name]=digest(p)
        sources={}
        for name in STEALTH_GODOT_TARGETS:
            p=w/'Godot'/name;previous=digest(p) if p.exists() else None
            source=w/'Source/Godot'/name;source.parent.mkdir(parents=True,exist_ok=True);source.write_text('stealth '+name)
            p.write_bytes(source.read_bytes());sources[str(source)]=digest(source)
            rows.append(dict(source=str(source),target=str(p),before_sha256=previous,after_sha256=digest(p)))
        build=w/'StealthLab/native_build.json';put(build,dict(passed=True,normal_binary_sha256=clock['native_after_sha256'],source_sha256=new_source,binaries_sha256=new_binary))
        real=w/'StealthLab/real.json';put(real,dict(passed=True,normal_runtime_unchanged=True,database_restored=True,source_inputs=sources))
        library='/DAoCVisualBridge/Stealth_v01/synthetic';assets={};mapping={}
        for i in range(2):
            p=plugin/('Content/Stealth_v01/synthetic/M_'+str(i)+'.uasset');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(('private synthetic material '+str(i)).encode())
            assets[str(p)]=digest(p);mapping['/Original/M_'+str(i)]=library+'/M_'+str(i)+'.M_'+str(i)
        material=w/'StealthLab/material-proof.json';put(material,dict(passed=True,checks=400,source_inputs=assets))
        catalog=plugin/'Content/ClassicUI/stealth_materials.json';put(catalog,dict(passed=True,library=library,materials=mapping))
        rows.append(dict(source=str(catalog),target=str(catalog),before_sha256=None,after_sha256=digest(catalog)))
        receipt=dict(installed=True,phase='complete',database_modified=False,server_rules_modified=False,
                     predecessor_receipt_sha256=digest(clock_path),native_before_sha256=clock['native_after_sha256'],native_after_sha256=new_binary['UnrealEditor-DAoCVisualBridge.dll'],
                     files=rows,godot_after_proof=str(real),material_proof=str(material),material_assets=assets,
                     evidence={str(p):digest(p) for p in [build,real,material]})
        receipt_path=w/'StealthLab/installed.json';put(receipt_path,receipt)
        def valid():assert verify_stealth_successor(w,clock,clock_path)[0]['installed']
        def rejected():
            try:verify_stealth_successor(w,clock,clock_path)
            except (AssertionError,KeyError,ValueError,FileNotFoundError):return
            raise AssertionError('Tampered stealth successor was accepted')
        valid();checks+=1
        for key in ['predecessor_receipt_sha256','native_before_sha256','native_after_sha256']:
            old=receipt[key];receipt[key]='0'*64;put(receipt_path,receipt);rejected();checks+=1;receipt[key]=old;put(receipt_path,receipt)
        for row in rows:
            for key in ['before_sha256','after_sha256']:
                old=row[key];row[key]='0'*64;put(receipt_path,receipt);rejected();checks+=1;row[key]=old;put(receipt_path,receipt)
        for p in [Path(r['target']) for r in rows]+[Path(a) for a in assets]+[build,real,material,prior_build,before]:
            old=p.read_bytes();p.write_bytes(b'tampered');rejected();checks+=1;p.write_bytes(old)
        receipt['files'].append(dict(target=str(w/'unrelated'),before_sha256=None,after_sha256='0'*64));put(receipt_path,receipt);rejected();checks+=1;receipt['files'].pop();put(receipt_path,receipt)
        valid();checks+=1
    result=dict(passed=True,checks=checks,synthetic_only=True,normal_installation_modified=False,test_source_sha256=digest(Path(__file__)))
    (workspace/'StealthLab/receipt_guard_tests.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.workspace.resolve())))
