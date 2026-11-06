"""Audit original packet-0xC9 event rows and stage a separate private catalog."""
import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sys
import struct
import tempfile
import wave
from prepare_combined_expansion_data import digest


def audit(workspace, install, stage=False):
    repo=Path(__file__).resolve().parents[3]
    pipeline=repo/'source/new-client/pipeline/build_sounds.py'
    os.environ['DAOC_CLIENT']=str(install/'runtime/client-opendaoc/app')
    sys.path.insert(0,str(pipeline.parent))
    spec=importlib.util.spec_from_file_location('original_server_audio',pipeline)
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    references={};dynamic=[];inputs=[pipeline,repo/'source/new-client/godot/game/net/DaocClient.cs',repo/'source/new-client/godot/game/net/server_world.gd']
    for path in sorted((repo/'source/server').rglob('*.cs')):
        text=path.read_text(encoding='utf-8-sig',errors='replace')
        if 'SendSoundEffect(' not in text:continue
        inputs.append(path)
        for match in re.finditer(r'\.SendSoundEffect\(\s*([^,]+),',text):
            value=match.group(1).strip()
            if value.isdecimal():references.setdefault(int(value),[]).append(str(path.relative_to(repo)))
            else:dynamic.append({'source':str(path.relative_to(repo)),'expression':value})
    # Preserve the upstream --events coverage; variable GM /cast arguments are
    # deliberately not guessed as static dependencies.
    ids=sorted(set(range(1,21))|set(references)|{163,216,217,218,219,220,2452,2467})
    table,_=builder.sound_tables();resolved={};missing=[]
    for sid in ids:
        row=table.get(sid);path=builder._find(row['file']) if row else None
        if not path:missing.append(sid);continue
        path=Path(path).resolve()
        resolved[str(sid)]={'name':row['name'],'original_file':str(path),'sha256':digest(path),'bytes':path.stat().st_size}
    inputs += [builder.CLIENT/'sounds/cc_sounds.csv',builder.CLIENT/'gamedata.mpk']
    report={'passed':bool(resolved) and all(str(sid) in resolved for sid in references),
        'packet':201,'static_server_ids':references,'dynamic_calls':dynamic,'requested_ids':ids,
        'resolved':resolved,'unresolved_ids':missing,'original_files':len({v['original_file'] for v in resolved.values()}),
        'input_hashes':{str(p):digest(p) for p in inputs},'production_modified':False,
        'scope':'Original server-requested one-shots; no ambient loops, music, quest state or world population changes'}
    out=workspace/'Reports/server_sound_audio';out.mkdir(parents=True,exist_ok=True)
    (out/'coverage.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if stage:
        assert report['passed'],missing
        root=workspace/'ServerSoundAudioLab';assert not (root/'installed.json').exists()
        builder.ROOT=root/'BuilderScratch';(builder.ROOT/'godot/content').mkdir(parents=True,exist_ok=True)
        builder.OUT=root/'OriginalServerSoundAudio_v01'
        with redirect_stdout(io.StringIO()):unresolved=builder.export(set(),set(),extra_ids=[int(k) for k in resolved])
        assert not unresolved,unresolved
        catalog=builder.OUT/'sounds.json';index=json.loads(catalog.read_text())
        files={str(builder.OUT/row['file']):digest(builder.OUT/row['file']) for row in index['sounds'].values()}
        conversions=[]
        for sid,row in index['sounds'].items():
            original=Path(resolved[sid]['original_file']);target=builder.OUT/row['file']
            if digest(original)==digest(target):continue
            chunks=builder._chunks(original.read_bytes());fmt=chunks[b'fmt ']
            assert struct.unpack('<H',fmt[:2])[0]==17,'Only original IMA ADPCM decompression is permitted'
            with tempfile.TemporaryDirectory(dir=root) as temporary:
                expected=Path(temporary)/'decoded.wav';builder._write_wav(original,expected)
                assert digest(expected)==digest(target)
            with wave.open(str(target),'rb') as decoded:
                assert decoded.getsampwidth()==2 and decoded.getnchannels()==struct.unpack('<H',fmt[2:4])[0]
                assert decoded.getframerate()==struct.unpack('<I',fmt[4:8])[0] and decoded.getnframes()>0
                if b'fact' in chunks:assert decoded.getnframes()==struct.unpack('<I',chunks[b'fact'][:4])[0]
            conversions.append({'id':int(sid),'source_sha256':digest(original),'pcm_sha256':digest(target),'reason':'Original IMA ADPCM decoded with existing upstream decoder; no replacement sound'})
        resources={'passed':True,'private_staging_only':True,'catalog':str(catalog),'catalog_sha256':digest(catalog),
            'files':files,'input_hashes':report['input_hashes'],'coverage_sha256':digest(out/'coverage.json'),'unresolved_ids':missing,'decompressed_originals':conversions}
        (root/'resources.json').write_text(json.dumps(resources,indent=2),encoding='utf-8')
    return {'passed':report['passed'],'static_server_ids':len(references),'resolved_ids':len(resolved),'original_files':report['original_files'],'unresolved_ids':missing,'staged':stage,'production_modified':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--stage',action='store_true');args=parser.parse_args()
    print(json.dumps(audit(args.workspace.resolve(),args.install.resolve(),args.stage)))
