"""Verify Shar delivery provenance, unchanged existing records and merged native acceptance."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(lab):
    lab=lab.resolve();delivery=lab/'Delivery'
    read=lambda path:json.loads(path.read_text(encoding='utf-8-sig'))
    digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    manifest=read(delivery/'manifest.json')
    assert manifest['passed'] and not manifest['installed']
    preserved={}
    for key,row in manifest['catalogues'].items():
        original,candidate=Path(row['target']),Path(row['candidate'])
        assert candidate.resolve().is_relative_to(delivery) and digest(original)==row['before_sha256'] and digest(candidate)==row['after_sha256']
        old,new=read(original),read(candidate)
        if key=='models':
            assert set(new)-set(old) <= {'1075','1087'}
            for ident,value in old.items():
                if ident not in ['1075','1087']:assert new[ident]==value
            preserved[key]=len(set(old)-{'1075','1087'})
        elif key=='appearance':
            for name,value in old.items():
                if name in ['figures','textures','original_color_textures']:
                    for ident,record in value.items():assert new[name][ident]==record
                else:assert new[name]==value
            assert set(new['figures'])-set(old['figures'])=={'1075','1087'}
            preserved[key]=len(old['figures'])
        else:
            for name,value in old.items():
                if name!='armour':assert new[name]==value
            for name,value in old['armour'].items():
                if name in ['figures','helmets']:
                    for ident,record in value.items():assert new['armour'][name][ident]==record
                else:assert new['armour'][name]==value
            assert 'starter_loadouts' not in new['armour']
            preserved[key]=len(old['armour']['figures'])
    targets=set()
    for row in manifest['assets']:
        source,target=Path(row['source']),Path(row['target'])
        assert str(target.resolve()) not in targets
        targets.add(str(target.resolve()))
        assert digest(source)==row['sha256'] and source.stat().st_size==row['bytes']
        if row['already_present']:assert target.exists() and digest(target)==row['sha256']
        else:assert not target.exists()
    for row in manifest['evidence']:assert digest(Path(row['path']))==row['sha256']
    native=lab/'MergedNativeAcceptance';raw=(native/'native.json').read_bytes()
    result=json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
    assert result['passed'] and result['checks']>=1598 and result['original_starter_loadouts_tested'] and not result['failures']
    inputs=read(native/'inputs.json')
    assert set(map(Path,inputs))=={delivery/'models.json',delivery/'appearance.json',delivery/'native_test_equipment.json'}
    for path,expected in inputs.items():assert digest(Path(path))==expected
    report={'passed':True,'installed':False,'assets':len(targets),'preserved_records':preserved,
        'merged_native_checks':result['checks'],'native_real_server':False,
        'native_inputs':inputs,'manifest_sha256':digest(delivery/'manifest.json'),
        'remaining_activation_gate':'Original Shar starts are outside supported native zone207; normal race options and server settings remain unchanged.'}
    (delivery/'verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--lab',type=Path,required=True)
    report=verify(parser.parse_args().lab)
    print(json.dumps(report))
