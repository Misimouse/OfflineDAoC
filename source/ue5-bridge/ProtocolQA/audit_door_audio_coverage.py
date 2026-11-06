"""Audit and optionally stage original door audio; never modify the normal client."""
import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import wave

from prepare_combined_expansion_data import digest


def audit(workspace, install, stage=False):
    repo=Path(__file__).resolve().parents[3]
    client=install/'runtime/client-opendaoc/app'
    pipeline=repo/'source/new-client/pipeline/build_sounds.py'
    os.environ['DAOC_CLIENT']=str(client)
    sys.path.insert(0,str(pipeline.parent))
    spec=importlib.util.spec_from_file_location('original_door_audio',pipeline)
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    _,names=builder.sound_tables()
    groups,queues,loops=builder.structures()
    doors={}
    for row in builder._rows('cc_doors.csv'):
        if row and row[0].strip().isdigit():
            doors[row[0].strip()]={'name':row[1].strip(),**{
                key:row[col].strip() for key,col in [('open',2),('close',3)]
                if len(row)>col and row[col].strip()}}
    leaves=set();visited=set();missing=set();cycles=set();loop_refs=set()
    def visit(name,trail=()):
        key=name.lower().strip()
        if not key or key=='s_null':return
        if key in trail:cycles.add(key);return
        if key in visited:return
        visited.add(key)
        if key in names:leaves.add(key);return
        if key in groups:members=groups[key]
        elif key in queues:members=queues[key]['members']
        elif key in loops:
            loop_refs.add(key)
            members=[v for k,v in loops[key].items() if k in ['start','body','stop'] and v]
        else:missing.add(key);return
        for member in members:visit(member,trail+(key,))
    for row in doors.values():
        for key in ['open','close']:
            if row.get(key):visit(row[key])
    files={};missing_files=[]
    for key in sorted(leaves):
        row=names[key];path=builder._find(row.get('file',row['name']))
        if not path:missing_files.append(key);continue
        path=Path(path).resolve();files[str(path)]={'sha256':digest(path),'bytes':path.stat().st_size}
    collision=workspace/'collision_catalog.json'
    catalog=json.loads(collision.read_text())
    fixtures=[fixture for model in catalog['models'].values() for fixture in model.get('door_fixtures',[])]
    door_ids=sorted({int(i) for fixture in fixtures for i in fixture.get('groups',{}).values()})
    inputs=[pipeline,collision,client/'sounds/cc_doors.csv',client/'sounds/cc_sounds.csv',
        client/'sounds/cc_groups.csv',client/'sounds/cc_queues.csv',client/'sounds/cc_loops.csv',
        repo/'source/new-client/godot/game/zone_door.gd',
        repo/'source/new-client/godot/game/net/DaocClient.cs',
        repo/'source/server/GameServer/packets/Server/PacketLib168.cs',
        repo/'source/ue5-bridge/Godot/live_gateway.gd',
        repo/'source/ue5-bridge/UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeDoors.cpp']
    report={'passed':not(missing_files or cycles or loop_refs),'coverage_complete':not missing,'installed':False,
        'normal_installation_modified':False,'original_door_sets':len(doors),'doors':doors,
        'required_named_rows':len(leaves),'unique_original_files':len(files),
        'original_bytes':sum(r['bytes'] for r in files.values()),
        'missing_structures':sorted(missing),'missing_files':missing_files,'cycles':sorted(cycles),
        'loop_structures_requiring_support':sorted(loop_refs),'loaded_fixture_door_ids':door_ids,
        'authoritative_rule':{'packet':'0x99','decoded_fields':['door_id','open','flag'],
            'zero_flag':'silent; do not invent an above-ground fallback in the bridge',
            'server_default':'flag 1 only for unflagged non-keep above-ground non-ToA doors',
            'one_voice_per_door_group':True,'repeated_state_is_silent':True,
            'join_hydration_requires_separate_witness':True},
        'missing_bridge_paths':['gateway discards sound flag','native door animation has no sound dispatch'],
        'files':files,'input_hashes':{str(p):digest(p) for p in inputs}}
    out=workspace/'Reports/door_audio';out.mkdir(parents=True,exist_ok=True)
    (out/'coverage.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if stage:
        assert report['passed'],'Original door coverage must resolve before staging'
        root=workspace/'DoorAudioLab';output=root/'OriginalDoorAudio_v01'
        assert not (root/'installed.json').exists(),'Sealed delivery root'
        builder.ROOT=root/'BuilderScratch';builder.OUT=output
        (builder.ROOT/'godot/content').mkdir(parents=True,exist_ok=True)
        roots={row[key] for row in doors.values() for key in ['open','close']
            if row.get(key) and row[key].lower() not in missing}
        with redirect_stdout(io.StringIO()):unresolved=builder.export(set(),set(),structure_names=sorted(roots))
        assert not unresolved,unresolved
        index_path=output/'sounds.json';index=json.loads(index_path.read_text())
        # Retain the authored structure names, including intentionally empty close slots.
        index['doors']={key:{k:v for k,v in row.items() if k=='name' or v.lower() not in missing}
            for key,row in doors.items()}
        index['unresolved_original_door_references']=sorted(missing)
        index_path.write_text(json.dumps(index,indent=1),encoding='utf-8')
        staged_files={row['file'] for row in index['named'].values()}
        assert len(staged_files)==len(files)
        for name in staged_files:
            with wave.open(str(output/name),'rb') as pcm:
                assert pcm.getcomptype()=='NONE' and pcm.getsampwidth()==2 and pcm.getnchannels() in [1,2]
        assert all(digest(Path(p))==sha for p,sha in report['input_hashes'].items())
        receipt={'passed':True,'installed':False,'private_staging_only':True,
            'original_client_unchanged':all(digest(Path(p))==row['sha256'] for p,row in files.items()),
            'catalog':str(index_path),'catalog_sha256':digest(index_path),
            'files':{str(output/name):digest(output/name) for name in sorted(staged_files)},
            'coverage_sha256':digest(out/'coverage.json')}
        assert receipt['original_client_unchanged']
        (root/'resources.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        report['private_staged']=True
    return {k:v for k,v in report.items() if k not in ['doors','files','input_hashes']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--stage',action='store_true')
    args=parser.parse_args();print(json.dumps(audit(args.workspace.resolve(),args.install.resolve(),args.stage)))
