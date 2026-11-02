import unreal,json,traceback
from pathlib import Path
R=Path(__file__).resolve().parent
known=json.loads((R/'collision_catalog.json').read_text(encoding='utf-8'))['models'];rows=[]
try:
 unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba')
 for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
  if a.get_editor_property('hidden'):continue
  for c in a.get_components_by_class(unreal.StaticMeshComponent):
   m=c.static_mesh
   if m is None or not c.get_editor_property('visible') or c.get_editor_property('hidden_in_game'):continue
   path=m.get_path_name();name=m.get_name().lower();tree=any(k in name for k in ['tree','oak','birch','elm','roble','olmo'])
   if tree or path not in known:
    n=c.get_instance_count() if isinstance(c,unreal.InstancedStaticMeshComponent) else 1
    if not n:continue
    row={'actor':a.get_actor_label(),'asset':path,'known':path in known,'tree':tree,'instances':n}
    try:
     box=m.get_bounding_box();row['min']=[box.min.x,box.min.y,box.min.z];row['max']=[box.max.x,box.max.y,box.max.z]
    except Exception as e:row['bounds_error']=str(e)
    rows.append(row)
 (R/'Reports/remote_collision/scene_audit.json').write_text(json.dumps({'passed':True,'rows':rows},indent=2),encoding='utf-8')
except Exception:
 (R/'Reports/remote_collision/scene_audit.json').write_text(json.dumps({'passed':False,'error':traceback.format_exc(),'rows':rows}),encoding='utf-8');raise
