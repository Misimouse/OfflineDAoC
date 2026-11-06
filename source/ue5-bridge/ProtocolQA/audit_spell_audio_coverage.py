"""Inventory original spell audio dependencies; no assets, catalogs or installations are changed."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from prepare_combined_expansion_data import digest


def audit(workspace, install):
    source=install/'new-client/godot/content/sounds'
    index_path=source/'sounds.json'
    index=json.loads(index_path.read_text())
    effects_path=workspace/'Client/Plugins/DAoCVisualBridge/Content/SpellVisuals_v01/catalog.json'
    effects=json.loads(effects_path.read_text())['effects']
    sets={int(row.get('sound_set',0)) for row in effects.values()}-{0}
    missing_sets=sorted(value for value in sets if str(value) not in index['spells'])
    missing_structures=set()
    cycles=set()
    names=set()
    structures=set()

    def visit(name, trail=()):
        key=name.strip().lower()
        if not key or key=='s_null':return
        if key in trail:
            cycles.add(key)
            return
        structures.add(key)
        if key in index['groups']:
            for child in index['groups'][key]:visit(child,trail+(key,))
        elif key in index['queues']:
            for child in index['queues'][key]['members']:visit(child,trail+(key,))
        elif key in index['named']:
            names.add(key)
        else:missing_structures.add(key)

    for value in sorted(sets):
        for event,name in index['spells'].get(str(value),{}).items():
            if event!='name':visit(name)
    files={index['named'][name]['file'] for name in names}
    missing_files=[]
    formats=Counter()
    rows=[]
    for name in sorted(files):
        path=(source/name).resolve()
        assert path.is_relative_to(source.resolve())
        if not path.exists():
            missing_files.append(name)
            continue
        raw=path.read_bytes()
        assert raw[:4]==b'RIFF' and raw[8:12]==b'WAVE',('Non-WAV original spell audio',name)
        offset=12
        chunks={}
        while offset+8<=len(raw):
            tag=raw[offset:offset+4]
            size=struct.unpack_from('<I',raw,offset+4)[0]
            assert offset+8+size<=len(raw),('Truncated WAV',name)
            chunks[tag]=raw[offset+8:offset+8+size]
            offset+=8+size+(size%2)
        assert b'fmt ' in chunks and len(chunks[b'fmt '])>=16 and b'data' in chunks
        codec,channels,rate,_,align,bits=struct.unpack_from('<HHIIHH',chunks[b'fmt '])
        formats[(codec,channels,bits)]+=1
        rows.append({'file':name,'sha256':digest(path),'bytes':len(raw),'codec':codec,'channels':channels,
                     'sample_rate':rate,'bits':bits,'data_bytes':len(chunks[b'data']),
                     'seconds':len(chunks[b'data'])/max(1,rate*align)})
    output=workspace/'Reports/spell_audio'
    output.mkdir(exist_ok=True)
    result={'passed':not(missing_sets or missing_structures or missing_files or cycles),
            'native_effect_definitions':len(effects),'required_sound_sets':len(sets),
            'missing_sound_sets':missing_sets,'missing_structures':sorted(missing_structures),
            'missing_files':missing_files,'structure_cycles':sorted(cycles),'named_rows':len(names),
            'structures':len(structures),'files':rows,'total_bytes':sum(row['bytes'] for row in rows),
            'formats':{str(key):value for key,value in formats.items()},
            'input_hashes':{str(index_path):digest(index_path),str(effects_path):digest(effects_path)},
            'normal_installation_modified':False,'scope':'Original spell sound sets only; excludes movement, weapon, creature, zone and interface audio'}
    (output/'coverage.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return {k:v for k,v in result.items() if k not in ['files','input_hashes']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(audit(args.workspace.resolve(),args.install.resolve())))
