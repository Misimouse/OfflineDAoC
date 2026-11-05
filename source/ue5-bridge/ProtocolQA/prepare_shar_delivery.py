"""Prepare merged Shar delivery catalogues without replacing installed catalogues or assets."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def prepare(workspace, lab):
    workspace, lab = workspace.resolve(), lab.resolve()
    assert lab.is_relative_to(workspace) and lab != workspace
    private = lab / 'NativeHost/Plugins/DAoCVisualBridge/Content'
    installed = workspace / 'Client/Plugins/DAoCVisualBridge/Content'
    assert private.resolve().is_relative_to(lab)
    output = lab / 'Delivery'
    output.mkdir(exist_ok=True)
    read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
    gates = ['outfit_exports_verified.json','native_outfit_import.json',
             'SourceHelmetsFull/verified.json','Reports/helmets/import.json',
             'HelmetFullAcceptance/native.json','StarterNativeAcceptance/native.json']
    evidence = []
    for name in gates:
        path = lab / name
        raw = path.read_bytes()
        report = json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))
        assert report['passed'], name
        evidence.append({'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()})
    for name in ['shar_starter_creation','shar_promotion']:
        path = workspace / 'Reports' / name / 'real_protocol.json'
        report = read(path)
        assert report['passed'] and len(report['cases']) == 10 and report['database_restored'] and report['appearance_profile_restored']
        evidence.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    source_paths = {'models':workspace/'models.json','equipment':workspace/'equipment_catalog_v01.json',
        'appearance':installed/'ClassicUI/Pregame/appearance_catalog.json'}
    before = {key:read(path) for key,path in source_paths.items()}
    merged = copy.deepcopy(before)
    candidate = read(lab/'models_outfits_candidate.json')
    for ident in ['1075','1087']:
        merged['models'][ident] = candidate[ident]
    figures = read(lab/'outfit_definitions_candidate.json')
    assert {row['base_id'] for row in figures.values()} == {'1075','1087'}
    for asset,row in figures.items():
        assert asset not in merged['equipment']['armour']['figures'] or merged['equipment']['armour']['figures'][asset] == row
        merged['equipment']['armour']['figures'][asset] = row
    helmets = read(lab/'equipment_helmets_full_candidate.json')['armour']['helmets']
    for ident in ['1075','1087']:
        assert len(helmets[ident]) == 163
        assert ident not in merged['equipment']['armour']['helmets'] or merged['equipment']['armour']['helmets'][ident] == helmets[ident]
        merged['equipment']['armour']['helmets'][ident] = helmets[ident]
    appearance = read(lab/'appearance_catalog_colour_candidate.json')
    for key in ['figures','textures','original_color_textures']:
        for ident,row in appearance[key].items():
            if key == 'textures' and ident.startswith('fro_'):
                continue
            assert ident not in merged['appearance'].get(key,{}) or merged['appearance'][key][ident] == row, ('Existing appearance entry differs',key,ident)
            merged['appearance'].setdefault(key,{})[ident] = row
    # Preserve approved global materials, skin calibration and unrelated race records.
    assert merged['appearance']['materials'] == before['appearance']['materials']
    for key in ['models','equipment','appearance']:
        (output/(key+'.json')).write_text(json.dumps(merged[key],indent=2),encoding='utf-8')
    native = copy.deepcopy(merged['equipment'])
    native['armour']['figures'] = figures
    native['armour']['helmets'] = {ident:helmets[ident] for ident in ['1075','1087']}
    native['armour']['starter_loadouts'] = read(lab/'equipment_starter_candidate.json')['armour']['starter_loadouts']
    (output/'native_test_equipment.json').write_text(json.dumps(native,indent=2),encoding='utf-8')
    roots = [p for folder,prefixes in [('ExpansionRaces_v01',['Model_1075_','Model_1087_']),
        ('ExpansionAppearance_v01',['sha_']),('ExpansionOutfits_v01',['sha_']),('ExpansionHelmets_v01',['sha_'])]
        for p in (private/folder).iterdir() if p.is_dir() and any(p.name.startswith(prefix) for prefix in prefixes)]
    files = []
    for folder in roots:
        for path in sorted(folder.rglob('*')):
            if not path.is_file():continue
            assert path.resolve().is_relative_to(private.resolve())
            relative = path.relative_to(private)
            target = installed/relative
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if target.exists():assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, ('Existing installed resource differs',str(target))
            files.append({'source':str(path),'target':str(target),'sha256':digest,'bytes':path.stat().st_size,'already_present':target.exists()})
    # Some original colour masks are shared texture assets outside the four
    # figure folders. Include every direct dependency of the added records.
    dependencies = set()
    def references(value):
        if isinstance(value,dict):
            for key,item in value.items():references(key);references(item)
        elif isinstance(value,list):
            for item in value:references(item)
        elif isinstance(value,str) and value.startswith('/DAoCVisualBridge/'):
            dependencies.add(value.split('.')[0].removeprefix('/DAoCVisualBridge/')+'.uasset')
    references({key:merged['models'][key] for key in ['1075','1087']})
    references(figures)
    references({key:helmets[key] for key in ['1075','1087']})
    references({key:merged['appearance'][key] for key in ['materials']})
    for key in ['figures','textures','original_color_textures']:
        references({name:value for name,value in merged['appearance'][key].items() if name not in before['appearance'].get(key,{})})
    indexed={str(Path(row['target']).resolve()) for row in files}
    for relative in sorted(dependencies):
        target=installed/relative
        assert target.resolve().is_relative_to(installed.resolve())
        if str(target.resolve()) in indexed:continue
        path=target if target.exists() else private/relative
        assert path.exists(), ('Missing direct Shar dependency',relative)
        files.append({'source':str(path),'target':str(target),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'already_present':target.exists()})
    report = {'passed':True,'installed':False,'scope':'Shar-only catalogues and original resources. No server library, race activation, normal assets or player database modified.',
        'evidence':evidence,'assets':files,'catalogues':{key:{'target':str(path),'before_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'candidate':str(output/(key+'.json')),'after_sha256':hashlib.sha256((output/(key+'.json')).read_bytes()).hexdigest()} for key,path in source_paths.items()},
        'preserved_global_materials':merged['appearance']['materials'],
        'pending':'Resolve shared approved-material dependencies and test these merged catalogues before installation.'}
    (output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['workspace','lab']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();report=prepare(args.workspace,args.lab)
    print(json.dumps({'passed':report['passed'],'assets':len(report['assets']),'bytes':sum(row['bytes'] for row in report['assets']),'installed':False}))
