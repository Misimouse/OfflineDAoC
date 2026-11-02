"""Read-only audit of the saved art map; no asset or map saves."""
import json,unreal
from pathlib import Path
ROOT=Path(__file__).resolve().parent
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba')
rows=[];lights=[];captures=[]
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    for c in actor.get_components_by_class(unreal.LightComponentBase):
        row=dict(actor=actor.get_actor_label(),type=c.get_class().get_name(),mobility=str(c.mobility))
        for prop in ['cast_shadows','intensity','dynamic_shadow_cascades','dynamic_shadow_distance_movable_light','dynamic_shadow_distance_stationary_light','real_time_capture']:
            try:row[prop]=c.get_editor_property(prop)
            except Exception:pass
        lights.append(row)
    for c in actor.get_components_by_class(unreal.SceneCaptureComponent):
        captures.append(dict(actor=actor.get_actor_label(),type=c.get_class().get_name(),every_frame=c.capture_every_frame))
    for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
        mesh=c.static_mesh
        if not mesh:continue
        row=dict(actor=actor.get_actor_label(),mesh=mesh.get_path_name(),count=c.get_instance_count(),
                 shadows=c.cast_shadow,start=c.instance_start_cull_distance,end=c.instance_end_cull_distance)
        try:row['height_cm']=mesh.get_bounds().box_extent.z*2
        except Exception:pass
        try:row['triangles']=mesh.get_num_triangles(0);row['vertices']=mesh.get_num_vertices(0)
        except Exception as error:row['geometry_error']=str(error)
        try:row['lods']=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_lod_count(mesh)
        except Exception as error:row['lod_error']=str(error)
        rows.append(row)
(ROOT/'Reports/performance/foliage_audit.json').write_text(json.dumps(rows,indent=2))
(ROOT/'Reports/performance/lighting_audit.json').write_text(json.dumps(dict(lights=lights,captures=captures),indent=2))
print('Read-only foliage audit:',len(rows),'components',sum(r['count'] for r in rows),'instances')
