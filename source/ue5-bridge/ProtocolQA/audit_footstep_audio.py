"""Audit and optionally stage original local-player footstep sounds, separately."""
import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
from prepare_combined_expansion_data import digest

def audit(workspace,install,stage=False):
    repo=Path(__file__).resolve().parents[3];pipeline=repo/'source/new-client/pipeline/build_sounds.py'
    client=install/'runtime/client-opendaoc/app';os.environ['DAOC_CLIENT']=str(client);sys.path.insert(0,str(pipeline.parent))
    spec=importlib.util.spec_from_file_location('original_step_audio',pipeline);builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    native_path=workspace/'models.json';native=json.loads(native_path.read_text());task_paths=[workspace/'SourceModels/tasks.json',workspace/'ExpansionRaceLab/OriginalTasks/tasks.json']
    tasks={str(row['id']):row for p in task_paths if p.exists() for row in json.loads(p.read_text()) if row.get('info',{}).get('race') or str(row['id'])=='1419'}
    sheets=builder.creature_sets();models={};unmapped=[];figure_paths=[]
    for mid,task in tasks.items():
        if mid not in native:continue
        info=task['info'];prefix=info.get('race','')
        if prefix:
            figure=install/'new-client/godot/content/characters/races'/prefix/'figure.json';figure_paths.append(figure)
            # Player._load_fig3 reads figure metadata, not the tutorial monster's
            # zero sound-set row. Preserve that same authoritative selection.
            meta=json.loads(figure.read_text());sid=int(meta.get('sound_set',0))
        else:sid=int(info.get('sound_set',0))
        if sid<=0 or sid not in sheets:unmapped.append(mid);continue
        models[mid]={'sound_set':sid,'race':prefix,'figure':info.get('figure',''),'clips':[clip for clip in ['run','walk','walk_back','strafe_left','strafe_right','swim'] if native[mid].get(clip)]}
    sets=sorted({row['sound_set'] for row in models.values()});_,names=builder.sound_tables();groups,queues,loops=builder.structures()
    roots={sheets[sid][event] for sid in sets for event in ['move_dirt','move_water'] if sheets[sid].get(event)}|{'g_Swimstroke_Small'}
    seen=set();leaves=set();missing=set();cycle=set();unsupported=set()
    def visit(name,trail=()):
        key=name.strip().lower()
        if not key or key=='s_null':return
        if key in trail:cycle.add(key);return
        if key in seen:return
        seen.add(key)
        if key in names:leaves.add(key);return
        if key in groups:children=groups[key]
        elif key in queues:children=queues[key]['members']
        elif key in loops:unsupported.add(key);return
        else:missing.add(key);return
        for child in children:visit(child,trail+(key,))
    for name in sorted(roots):visit(name)
    files={};missing_files=[]
    for key in sorted(leaves):
        row=names[key];p=builder._find(row.get('file',row['name']))
        if not p:missing_files.append(key);continue
        p=Path(p).resolve();files[str(p)]={'sha256':digest(p),'bytes':p.stat().st_size}
    inputs=[native_path,pipeline,repo/'source/new-client/godot/game/character_sounds.gd',repo/'source/new-client/godot/game/player.gd',client/'gamedata.mpk']+[p for p in task_paths if p.exists()]+figure_paths
    inputs += [client/'sounds'/name for name in ['cc_sounds.csv','cc_creatures.csv','cc_groups.csv','cc_queues.csv','cc_loops.csv']]
    report={'passed':not(missing or missing_files or cycle or unsupported or unmapped),'normal_installation_modified':False,'models':models,'required_sets':sets,'original_files':files,
        'missing_structures':sorted(missing),'missing_files':missing_files,'cycles':sorted(cycle),'unsupported_loops':sorted(unsupported),'unmapped_player_models':unmapped,
        'input_hashes':{str(p):digest(p) for p in inputs},'contact_reference':{'samples':96,'threshold_fraction':.12,'minimum_motion_m':.02,'merge_seconds':.15,'maximum_one_sound_per_frame':True,'npc_steps':False,'stablemaster_gallop':False}}
    out=workspace/'Reports/footstep_audio';out.mkdir(parents=True,exist_ok=True);(out/'coverage.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if stage:
        assert report['passed'],{'unmapped':unmapped,'missing':sorted(missing),'missing_files':missing_files,'loops':sorted(unsupported),'cycles':sorted(cycle)}
        root=workspace/'FootstepAudioLab';assert not (root/'installed.json').exists()
        output=root/'OriginalFootstepAudio_v01';output.mkdir(parents=True,exist_ok=True)
        original=builder.creature_sets;builder.creature_sets=lambda:{sid:{key:value for key,value in row.items() if key in ['name','move_dirt','move_water']} for sid,row in original().items()}
        builder.ROOT=root/'BuilderScratch';(builder.ROOT/'godot/content').mkdir(parents=True,exist_ok=True);builder.OUT=output
        with redirect_stdout(io.StringIO()):unresolved=builder.export(set(),set(),creature_set_ids=sets,structure_names=['g_Swimstroke_Small'])
        assert not unresolved,unresolved
        catalog=output/'sounds.json';index=json.loads(catalog.read_text());index['local_player_models']=models;catalog.write_text(json.dumps(index,indent=1),encoding='utf-8')
        resource_files={str(output/name):digest(output/name) for name in sorted({row['file'] for row in index['named'].values()})}
        assert len(resource_files)==len(files)
        assert all(digest(Path(p))==sha for p,sha in report['input_hashes'].items())
        resources={'passed':True,'installed':False,'private_staging_only':True,'catalog':str(catalog),'catalog_sha256':digest(catalog),'files':resource_files,'input_hashes':report['input_hashes'],'coverage_sha256':digest(out/'coverage.json')}
        (root/'resources.json').write_text(json.dumps(resources,indent=2),encoding='utf-8')
    return {'passed':report['passed'],'player_models':len(models),'sound_sets':len(sets),'original_files':len(files),'original_bytes':sum(row['bytes'] for row in files.values()),'unmapped':unmapped,'missing':sorted(missing),'staged':stage,'normal_installation_modified':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--stage',action='store_true');args=parser.parse_args();print(json.dumps(audit(args.workspace.resolve(),args.install.resolve(),args.stage)))
