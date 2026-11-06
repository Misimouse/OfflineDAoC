"""Stage original spell WAVs privately using the existing Godot decoder and tables."""
import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sys

from prepare_combined_expansion_data import digest


def prepare(workspace, install):
    repo=Path(__file__).resolve().parents[3]
    client=install/'runtime/client-opendaoc/app'
    tables={name:client/'sounds'/name for name in ['cc_sounds.csv','cc_spells.csv','cc_groups.csv','cc_queues.csv']}
    source_hashes={str(path):digest(path) for path in tables.values()}
    os.environ['DAOC_CLIENT']=str(client)
    pipeline=repo/'source/new-client/pipeline/build_sounds.py'
    sys.path.insert(0,str(pipeline.parent))
    spec=importlib.util.spec_from_file_location('original_spell_audio_builder',pipeline)
    sounds=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sounds)
    root=workspace/'SpellAudioLab'
    output=root/'OriginalAudio_v01'
    output.mkdir(parents=True,exist_ok=True)
    sounds.ROOT=root/'BuilderScratch'
    (sounds.ROOT/'godot/content').mkdir(parents=True,exist_ok=True)
    sounds.OUT=output
    sounds.CLIENT=client
    sounds.SOUND_DIR=client/'sounds'
    fx_path=workspace/'Client/Plugins/DAoCVisualBridge/Content/SpellVisuals_v01/catalog.json'
    effects=json.loads(fx_path.read_text())['effects']
    ids=sorted({int(row.get('sound_set',0)) for row in effects.values()}-{0})
    with redirect_stdout(io.StringIO()):
        missing=sounds.export(set(),set(),spell_set_ids=ids)
    assert missing==['spell set 332'], ('Unexpected original spell audio gap',missing)
    index=json.loads((output/'sounds.json').read_text())
    assert index['original_name_aliases']==sounds.SPELL_NAME_ALIASES
    for alias,original in sounds.SPELL_NAME_ALIASES.items():
        assert index['named'][alias]==index['named'][original]
        assert index['named'][alias]['id'] in [2125,2126,2127]
    assert all(digest(Path(path))==sha for path,sha in source_hashes.items())
    files={row['file'] for row in index['named'].values()}
    assert len(files)==184
    inputs=dict(source_hashes,**{str(fx_path):digest(fx_path),str(pipeline):digest(pipeline)})
    result={'passed':True,'installed':False,'private_staging_only':True,'original_client_unchanged':True,
            'known_original_missing_sound_sets':[332],'original_spelling_aliases':sounds.SPELL_NAME_ALIASES,
            'spell_sound_sets':len(index['spells']),'files':{str(output/name):digest(output/name) for name in sorted(files)},
            'total_bytes':sum((output/name).stat().st_size for name in files),'input_hashes':inputs,
            'catalog_sha256':digest(output/'sounds.json'),'catalog':str(output/'sounds.json')}
    (root/'resources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return {k:v for k,v in result.items() if k not in ['files','input_hashes']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.workspace.resolve(),args.install.resolve())))
