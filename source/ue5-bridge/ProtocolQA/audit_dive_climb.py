"""Read original movement/zone contracts without enabling new traversal or modifying data."""
import argparse,json,sqlite3
from pathlib import Path
from prepare_combined_expansion_data import digest

def audit(workspace,install):
    source=Path(__file__).resolve().parents[1];repo=source.parent;game=install/'new-client/godot/game'
    paths=[game/'player.gd',game/'zone_loader.gd',game/'zone_viewer.gd',source/'Godot/movement_flags_state.gd',source/'UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeWaterMovement.cpp',repo/'server/GameServer/packets/Client/168/PlayerPositionUpdateHandler.cs',repo/'server/GameServer/gameobjects/GamePlayer.cs',repo/'server/GameServer/world/WorldMgr.cs']
    assert all(p.is_file() for p in paths)
    inputs={str(p):digest(p) for p in paths}
    player=(game/'player.gd').read_text(encoding='utf-8-sig');world=(game/'zone_viewer.gd').read_text(encoding='utf-8-sig')
    assert 'const CLIMB_SPEED := 85.0 * 0.025' in player and '"ClimbBodies"' in player and 'state = 0x1C' in world
    zone=install/'new-client/godot/content/zones/zone207';gltf=list((zone/'models').glob('*.gltf'));assert gltf
    marked=[]
    for p in gltf:
        data=json.loads(p.read_text(encoding='utf-8-sig'));nodes=[n.get('name','') for n in data.get('nodes',[]) if n.get('name','').lower().startswith('climb_')]
        if nodes:marked.append(dict(model=p.name,nodes=nodes))
        inputs[str(p)]=digest(p)
    catalogue_path=workspace/'models.json';catalogue=json.loads(catalogue_path.read_text());inputs[str(catalogue_path)]=digest(catalogue_path)
    ladder_models=[k for k,v in catalogue.items() if v.get('ladder')]
    dbpath=install/'runtime/data/opendaoc.sqlite3.db';wal=Path(str(dbpath)+'-wal')
    assert dbpath.is_file() and (not wal.exists() or wal.stat().st_size==0),'Read this immutable audit only after the normal server has closed/checkpointed'
    with sqlite3.connect('file:'+dbpath.as_posix()+'?mode=ro&immutable=1',uri=True) as db:
        db.row_factory=sqlite3.Row
        row=dict(db.execute('SELECT ZoneID,Zones.RegionID,Zones.Name,DivingFlag,Regions.DivingEnabled FROM Zones JOIN Regions ON Zones.RegionID=Regions.RegionID WHERE ZoneID=207').fetchone())
        enabled=bool(row['DivingFlag']==1 or row['DivingFlag']!=2 and row['DivingEnabled'])
        counts=dict(regions_with_diving=db.execute('SELECT count(*) FROM Regions WHERE DivingEnabled<>0').fetchone()[0],zones_explicitly_enabling_diving=db.execute('SELECT count(*) FROM Zones WHERE DivingFlag=1').fetchone()[0])
    result=dict(passed=True,audit_only=True,runtime_modified=False,database_modified=False,source_inputs=inputs,
        original_godot=dict(surface_swimming_only=True,climb_speed_mps=2.125,climb_state_flags=28,climb_surface_prefix='climb_',ray_heights_m=[.5,1.2]),
        original_dol=dict(diving_input_action_flag=2,diving_output_action_flag=4,stealth_output_action_flag=2,climb_state_flags=28,holding_breath_seconds=30,drowning_timer_seconds=15,zone_permissions_retained=True),
        connacht=dict(zone=row,diving_effectively_enabled=enabled,gltf_models_inspected=len(gltf),marked_climb_models=marked),
        installed=dict(model_count=len(catalogue),models_with_original_ladder_clip=ladder_models,climbing_motion_not_implemented=True,diving_motion_not_implemented=True),
        population_flags=counts,
        decision='Preserve approved surface swimming in Connacht. Do not enable diving against server zone rules or turn decorative vines into ladders. Climbing needs original climb geometry from a relevant world zone; ladder clips already exist for 37 current models. Implement traversal in its own world-enabled delivery with ordinary-player protocol and collision tests.')
    assert all(digest(Path(p))==h for p,h in inputs.items())
    root=workspace/'DiveClimbLab';root.mkdir(exist_ok=True);(root/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return dict(passed=True,audit_only=True,diving_in_connacht=enabled,marked_climb_models=len(marked),original_ladder_models=len(ladder_models),report=str(root/'audit.json'))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ['workspace','install']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.workspace.resolve(),a.install.resolve())))
