"""Read-only original creature/weapon sound coverage for the current native models."""
import argparse
from collections import Counter
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import sys

from prepare_combined_expansion_data import digest


def audit(workspace, install):
    repo=Path(__file__).resolve().parents[3]
    pipeline=repo/'source/new-client/pipeline/build_sounds.py'
    client=install/'runtime/client-opendaoc/app'
    os.environ['DAOC_CLIENT']=str(client)
    sys.path.insert(0,str(pipeline.parent))
    spec=importlib.util.spec_from_file_location('original_combat_audio',pipeline)
    builder=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    _,names=builder.sound_tables()
    groups,queues,loops=builder.structures()
    creatures=builder.creature_sets()
    weapons=builder.weapon_sets()
    original=builder.read_mpk(str(client/'gamedata.mpk'))
    rows={r[0].strip():r for r in csv.reader(io.StringIO(original['monsters.csv'].decode('latin1')))
          if len(r)>15 and r[0].strip().isdigit()}
    native_path=workspace/'models.json'
    native=json.loads(native_path.read_text())
    mappings={}
    absent=[]
    for model in native:
        r=rows.get(model)
        if r is None:absent.append(model);continue
        mappings[model]=int(r[15]) if r[15].strip().isdigit() else 0
    used_sets=sorted(set(mappings.values())-{0})
    missing_sets=sorted(set(used_sets)-creatures.keys())
    # Limit this audit to attack, hurt, defense and death. Footstep contact timing,
    # idle calls and mounted/swim audio require a separate implementation witness.
    events=['attack','pain_light','pain_medium','pain_heavy','die','evade','splat']
    roots={str(row[k]).strip() for sid,row in creatures.items() if sid in used_sets for k in events if row.get(k)}
    roots|={str(row[k]).strip() for row in weapons.values() for k in builder.WEAPON_COLUMNS if row.get(k)}
    structures=set();leaves=set();missing=set();cycles=set();loop_refs=set()

    def visit(name,trail=()):
        key=name.strip().lower()
        if not key or key=='s_null':return
        if key in trail:cycles.add(key);return
        if key in structures:return
        structures.add(key)
        if key in names:leaves.add(key);return
        if key in groups:members=groups[key]
        elif key in queues:members=queues[key]['members']
        elif key in loops:
            loop_refs.add(key)
            members=[value for k,value in loops[key].items() if k in ['start','body','stop'] and value]
        else:missing.add(key);return
        for child in members:visit(child,trail+(key,))

    for name in sorted(roots):visit(name)
    files={};missing_files=[]
    for key in sorted(leaves):
        row=names[key]
        path=builder._find(row['file']) if 'file' in row else builder._find(row['name'])
        if not path:missing_files.append(key);continue
        path=Path(path).resolve()
        files[str(path)]={'sha256':digest(path),'bytes':path.stat().st_size}
    inputs=[native_path,pipeline,repo/'source/new-client/godot/game/net/server_world.gd',
            repo/'source/ue5-bridge/Godot/combat_visual_state.gd',client/'gamedata.mpk']
    inputs.extend(repo/'source/server/GameServer'/name for name in ['packets/Server/PacketLib186.cs','spells/SpellHandler.cs'])
    inputs.extend(client/'sounds'/name for name in ['cc_sounds.csv','cc_creatures.csv','cc_weapons.csv','cc_groups.csv','cc_queues.csv','cc_loops.csv'])
    report={'passed':not(missing_sets or missing or missing_files or cycles or loop_refs),
        'normal_installation_modified':False,'scope':'original combat creature vocals and weapon events; no footsteps/idle/zone audio',
        'native_models':len(native),'native_models_without_original_row':sorted(absent,key=int),
        'native_model_sound_sets':mappings,'silent_model_rows':sum(sid==0 for sid in mappings.values()),
        'required_creature_sets':len(used_sets),'original_weapon_sets':len(weapons),
        'missing_creature_sets':missing_sets,'missing_structures':sorted(missing),
        'missing_files':missing_files,'cycles':sorted(cycles),'loop_structures_requiring_support':sorted(loop_refs),
        'required_named_rows':len(leaves),'unique_original_files':len(files),
        'original_bytes':sum(row['bytes'] for row in files.values()),
        'file_extensions':dict(Counter(Path(path).suffix.lower() for path in files)),
        'files':files,'input_hashes':{str(path):digest(path) for path in inputs},
        'dispatch_reference':{'spell_result':20,'bow_prepare':16000,'bow_shoot':16003,'weaponless_set':19,'pain_throttle_ms':700,
            'health_fraction_medium_threshold':0.1,'no_melee_swing_for_spell_damage':True,
            'source':'source/new-client/godot/game/net/server_world.gd:_combat_sounds'}}
    out=workspace/'Reports/combat_audio'
    out.mkdir(parents=True,exist_ok=True)
    (out/'coverage.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return {k:v for k,v in report.items() if k not in ['native_model_sound_sets','files','input_hashes']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(audit(args.workspace.resolve(),args.install.resolve())))
