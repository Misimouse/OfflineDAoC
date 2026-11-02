"""Read-only saved-world survey for door/bridge/stair traversal review."""
import hashlib,json,traceback
from pathlib import Path
import unreal
R=Path(__file__).resolve().parent;out=R/'Reports/navigation/traversal';out.mkdir(parents=True,exist_ok=True)
report={'complete':False,'components':[],'meshes':{},'errors':[]}
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba')
    registry=unreal.AssetRegistryHelpers.get_asset_registry();registry.scan_paths_synchronous(['/DAoCVisualBridge/NavigationCollision_v01'],True)
    catalog=json.loads((R/'collision_catalog.json').read_text())['models']
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if actor.get_editor_property('hidden'):continue
        for c in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh=c.static_mesh
            if not mesh or not c.get_editor_property('visible') or c.get_editor_property('hidden_in_game'):continue
            path=mesh.get_path_name();record=catalog.get(path)
            if not record or record['kind']!='structure':continue
            t=c.get_world_transform();b=c.get_local_bounds()
            row={'actor':actor.get_actor_label(),'component':c.get_path_name(),'mesh':path,
                 'position':list(t.translation.to_tuple()),'rotation':list(t.rotation.to_tuple()),'scale':list(t.scale3d.to_tuple()),
                 'bounds_local':[list(v.to_tuple()) for v in b]}
            report['components'].append(row)
            if path in report['meshes']:continue
            # Visual geometry is authoritative for openings, private copy for physics.
            dm=unreal.DynamicMesh();ld=unreal.GeometryScriptMeshReadLOD();ld.lod_type=unreal.GeometryScriptLODType.RENDER_DATA;ld.lod_index=0
            _,result=unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh,dm,unreal.GeometryScriptCopyMeshFromAssetOptions(),ld,use_section_materials=False)
            assert 'SUCCESS' in str(result).upper(),path
            vs=unreal.GeometryScript_List.convert_vector_list_to_array(unreal.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)[1])
            ts=unreal.GeometryScript_List.convert_triangle_list_to_array(unreal.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)[1])
            mids=unreal.GeometryScript_List.convert_index_list_to_array(unreal.GeometryScript_Materials.get_all_triangle_material_i_ds(dm)[1])
            name=hashlib.sha256(path.encode()).hexdigest()[:12]+'.json'
            (out/name).write_text(json.dumps({'vertices':[list(v.to_tuple()) for v in vs], 'triangles':[list(t.to_tuple()) for t in ts], 'materials':list(mids)}))
            report['meshes'][path]={'file':name,'triangles':len(ts),'collision':record['asset'],
                'material_slots':[str(s.material_slot_name) for s in mesh.get_editor_property('static_materials')]}
    report['complete']=True
except Exception:report['errors'].append(traceback.format_exc());raise
finally:(out/'survey.json').write_text(json.dumps(report,indent=2))
