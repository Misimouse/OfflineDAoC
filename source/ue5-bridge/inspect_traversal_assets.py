import json,unreal
from pathlib import Path
R=Path(__file__).resolve().parent;A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/DAoCVisualBridge/NavigationCollision_v02'],True)
out={}
for name in ['SM_helfshack_Doorway','SM_elftavern2_Doorway','SM_helfshack_Leaf_0','SM_elftavern2_Leaf_1']:
    mesh=A.load_asset('/DAoCVisualBridge/NavigationCollision_v02/'+name);r={'triangles':mesh.get_num_triangles(0)}
    for prop in ['lod_for_collision','complex_collision_mesh']:
        try:r[prop]=str(mesh.get_editor_property(prop))
        except:r[prop]='unavailable'
    dm=unreal.DynamicMesh();ld=unreal.GeometryScriptMeshReadLOD();ld.lod_type=unreal.GeometryScriptLODType.RENDER_DATA;ld.lod_index=0
    unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh,dm,unreal.GeometryScriptCopyMeshFromAssetOptions(),ld,use_section_materials=False)
    r['vertices']=[list(v.to_tuple()) for v in unreal.GeometryScript_List.convert_vector_list_to_array(unreal.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)[1])]
    r['indices']=[list(t.to_tuple()) for t in unreal.GeometryScript_List.convert_triangle_list_to_array(unreal.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)[1])]
    out[name]=r
(R/'Reports/navigation/traversal/private_geometry.json').write_text(json.dumps(out))
