"""Private derivatives only: leave the artistic map and all /Game meshes untouched."""
import json,traceback
from pathlib import Path
import unreal
R=Path(__file__).resolve().parent;report={'complete':False,'assets':[],'errors':[]}
try:
    A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);T=unreal.AssetToolsHelpers.get_asset_tools();E=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.StaticMeshEditorSubsystem()
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/DAoCVisualBridge/NavigationCollision_v02'],True)
    splits=json.loads((R/'Reports/navigation/traversal/door_splits.json').read_text());catalog=json.loads((R/'collision_catalog.json').read_text())
    def bake(source,name,geometry,pivot=(0,0,0),keep=False):
        dm=unreal.DynamicMesh();ld=unreal.GeometryScriptMeshReadLOD();ld.lod_type=unreal.GeometryScriptLODType.RENDER_DATA;ld.lod_index=0
        _,result=unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(source,dm,unreal.GeometryScriptCopyMeshFromAssetOptions(),ld,use_section_materials=False)
        assert 'SUCCESS' in str(result).upper()
        # StaticMesh rebuilds may reorder triangles. Match geometry, never stale IDs.
        def key(triangle):return tuple(sorted(tuple(round(float(v),2)for v in point)for point in triangle))
        wanted={key(t)for t in geometry}
        vertices=unreal.GeometryScript_List.convert_vector_list_to_array(unreal.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)[1])
        triangles=unreal.GeometryScript_List.convert_triangle_list_to_array(unreal.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)[1])
        _,valid,_=unreal.GeometryScript_MeshQueries.get_all_triangle_i_ds(dm)
        valid=set(unreal.GeometryScript_List.convert_index_list_to_array(valid));matched=set();seen=set()
        for tid in valid:
            tri=triangles[tid];k=key([vertices[i].to_tuple() for i in (tri.x,tri.y,tri.z)])
            if k in wanted:matched.add(tid);seen.add(k)
        assert seen==wanted,(name,'source geometry changed',len(wanted-seen))
        remove=sorted(valid-matched if keep else matched)
        ids=unreal.GeometryScript_List.convert_array_to_index_list(remove)
        _,deleted=unreal.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm,ids)
        # Render data may contain degenerate triangles omitted by DynamicMesh.
        assert deleted>0 and deleted<=len(remove),(deleted,len(remove))
        assert dm.get_triangle_count()==(len(matched) if keep else len(valid)-len(matched)),name
        if any(pivot):unreal.GeometryScript_MeshTransforms.translate_mesh(dm,unreal.Vector(*[-p for p in pivot]))
        target='/DAoCVisualBridge/NavigationCollision_v02/'+name
        mesh=A.load_asset(target) if A.does_asset_exist(target)else T.duplicate_asset(name,'/DAoCVisualBridge/NavigationCollision_v02',source)
        options=unreal.GeometryScriptCopyMeshToAssetOptions();options.replace_materials=False
        _,result=unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,mesh,options,unreal.GeometryScriptMeshWriteLOD())
        assert 'SUCCESS' in str(result).upper(),str(result)
        E.remove_collisions(mesh)
        body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE);body.set_editor_property('double_sided_geometry',True)
        for section in range(mesh.get_num_sections(0)):E.enable_section_collision(mesh,True,0,section)
        A.save_loaded_asset(mesh,only_if_is_dirty=False);report['assets'].append(mesh.get_path_name());return mesh
    for path,data in splits.items():
        source=A.load_asset(path);assert source,path
        static=bake(source,'SM_'+source.get_name()+'_Doorway',data['remove_triangles'])
        entry=catalog['models'][path];entry['asset']=static.get_path_name();entry['visual_asset']=static.get_path_name();entry['door_fixtures']=data['fixtures'];entry['door_leaves']=[]
        for leaf in data['leaves']:
            mesh=bake(source,'SM_'+source.get_name()+'_Leaf_'+str(leaf['id']),leaf['triangles'],leaf['pivot_cm'],True)
            entry['door_leaves'].append({k:v for k,v in leaf.items()if k not in ('triangle_ids','triangles')}|{'asset':mesh.get_path_name()})
    # The shop's short foundation bevel is 59 degrees. Allow that exact low
    # surface as a ramp without making its fabric walls or roof walkable.
    survey=json.loads((R/'Reports/navigation/traversal/survey.json').read_text())
    shop=next(p for p in survey['meshes'] if p.endswith('/hshop.hshop'))
    geometry=json.loads((R/'Reports/navigation/traversal'/survey['meshes'][shop]['file']).read_text())
    low=[[[float(v) for v in geometry['vertices'][i]] for i in tri] for tri in geometry['triangles'] if max(geometry['vertices'][i][2] for i in tri)<65]
    source=A.load_asset(shop);walls=bake(source,'NC_hshop_Upper',low);foundation=bake(source,'NC_hshop_Foundation',low,keep=True)
    catalog['models'][shop]['asset']=walls.get_path_name()
    catalog['models'][shop]['sub_colliders']=[{'asset':foundation.get_path_name(),'walkable_angle':65}]
    # A sky sphere and tiny path pebbles never form gameplay barriers.
    catalog['models'].pop('/Engine/BasicShapes/Sphere.Sphere',None)
    for key in list(catalog['models']):
        if 'Connacht_Path_v01_Pebbles' in key:catalog['models'].pop(key)
    catalog['version']=2;(R/'collision_catalog.json').write_text(json.dumps(catalog,indent=2))
    report['complete']=True
except Exception:report['errors'].append(traceback.format_exc());raise
finally:(R/'Reports/navigation/door_asset_build.json').write_text(json.dumps(report,indent=2))
