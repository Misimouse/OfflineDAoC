"""Stage original combat audio separately; never alter the installed spell catalog."""
import argparse
from contextlib import redirect_stdout
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import wave

from prepare_combined_expansion_data import digest


def prepare(workspace, install):
    repo=Path(__file__).resolve().parents[3]
    audit_path=workspace/'Reports/combat_audio/coverage.json'
    audit=json.loads(audit_path.read_text())
    assert audit['passed'] and not audit['normal_installation_modified']
    assert all(digest(Path(p))==sha for p,sha in audit['input_hashes'].items())
    assert all(digest(Path(p))==row['sha256'] for p,row in audit['files'].items())
    client=install/'runtime/client-opendaoc/app'
    os.environ['DAOC_CLIENT']=str(client)
    pipeline=repo/'source/new-client/pipeline/build_sounds.py'
    sys.path.insert(0,str(pipeline.parent))
    spec=importlib.util.spec_from_file_location('original_combat_audio_builder',pipeline)
    builder=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    all_creatures=builder.creature_sets()
    allowed=['name','attack','pain_light','pain_medium','pain_heavy','die','evade','splat']
    builder.creature_sets=lambda:{key:{k:v for k,v in row.items() if k in allowed} for key,row in all_creatures.items()}
    sets=sorted(set(audit['native_model_sound_sets'].values())-{0})
    weapon_sets=sorted(builder.weapon_sets())
    root=workspace/'CombatAudioLab'
    output=root/'OriginalCombatAudio_v01'
    output.mkdir(parents=True,exist_ok=True)
    builder.ROOT=root/'BuilderScratch'
    (builder.ROOT/'godot/content').mkdir(parents=True,exist_ok=True)
    builder.OUT=output
    with redirect_stdout(io.StringIO()):
        missing=builder.export(set(),set(),creature_set_ids=sets,weapon_set_ids=weapon_sets)
    assert not missing,missing
    catalog=output/'sounds.json'
    index=json.loads(catalog.read_text())
    gamedata=builder.read_mpk(str(client/'gamedata.mpk'))
    weapon_models={}
    for row in csv.reader(io.StringIO(gamedata['objects.csv'].decode('latin1'))):
        if len(row)>21 and row[0].strip().isdigit() and row[21].strip().isdigit():
            sid=int(row[21])
            if sid>0:weapon_models[row[0].strip()]={'sound_set':sid}
    index['combat_model_sets']=audit['native_model_sound_sets']
    index['combat_weapon_models']=weapon_models
    catalog.write_text(json.dumps(index,indent=1),encoding='utf-8')
    files={row['file'] for row in index['named'].values()}
    assert len(files)==audit['unique_original_files']
    formats=set()
    for name in files:
        with wave.open(str(output/name),'rb') as stream:
            assert stream.getcomptype()=='NONE' and stream.getsampwidth()==2 and stream.getnchannels() in [1,2]
            formats.add((stream.getnchannels(),stream.getsampwidth(),stream.getframerate()))
    assert all(digest(Path(p))==sha for p,sha in audit['input_hashes'].items())
    report={'passed':True,'installed':False,'private_staging_only':True,'original_client_unchanged':True,
        'audit_sha256':digest(audit_path),'catalog':str(catalog),'catalog_sha256':digest(catalog),
        'files':{str(output/name):digest(output/name) for name in sorted(files)},
        'total_bytes':sum((output/name).stat().st_size for name in files),'creature_sets':len(sets),
        'weapon_sets':len(weapon_sets),'weapon_model_mappings':len(weapon_models),'formats':[list(row) for row in sorted(formats)],
        'input_hashes':dict(audit['input_hashes'],**{str(audit_path):digest(audit_path)})}
    (root/'resources.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return {k:v for k,v in report.items() if k not in ['files','input_hashes']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.workspace.resolve(),args.install.resolve())))
