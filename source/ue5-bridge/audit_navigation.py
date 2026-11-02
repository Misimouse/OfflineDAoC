"""Inspect saved collision and source metadata; never save the art level."""
import json,unreal
from pathlib import Path
R=Path(__file__).resolve().parent
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba')
rows=[];counts={}
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    for c in actor.get_components_by_class(unreal.StaticMeshComponent):
        mesh=c.static_mesh
        if mesh is None:continue
        mode=str(c.get_collision_enabled());counts[mode]=counts.get(mode,0)+1
        if 'NO_COLLISION' in mode:continue
        body=mesh.get_editor_property('body_setup')
        row={'actor':actor.get_actor_label(),'mesh':mesh.get_path_name(),'mode':mode,'instances':c.get_instance_count() if isinstance(c,unreal.InstancedStaticMeshComponent) else 1,'transform':str(c.get_world_transform()),'trace':str(body.get_editor_property('collision_trace_flag')) if body else None}
        rows.append(row)
(R/'Reports/navigation').mkdir(exist_ok=True,parents=True)
(R/'Reports/navigation/source_collision.json').write_text(json.dumps({'counts':counts,'colliders':rows},indent=2))
print('NAVIGATION_AUDIT',counts,'active',len(rows))
