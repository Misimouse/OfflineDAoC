"""Create private query-only collision resources from the saved scene. Never save its map."""
import hashlib,json,traceback
from pathlib import Path
import unreal
R=Path(__file__).resolve().parent
report={'complete':False,'models':{},'errors':[]};output=R/'Reports/navigation/collision_build.json'
def save():output.write_text(json.dumps(report,indent=2))
try:
    A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);T=unreal.AssetToolsHelpers.get_asset_tools()
    E=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.StaticMeshEditorSubsystem()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba')
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/DAoCVisualBridge/NavigationCollision_v01','/DAoCVisualBridge/RuntimeProfiles_v01','/DAoCVisualBridge/PerformanceLOD_v01'],force_rescan=True)
    lods=json.loads((R/'foliage_lods.json').read_text());sources={}
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if actor.get_editor_property('hidden'):continue
        for c in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh=c.static_mesh
            if mesh is None or not c.get_editor_property('visible'):continue
            path=mesh.get_path_name();name=mesh.get_name().lower()
            if '/Player_Trial_v01/Collision/' in path or any(s in name for s in ['sky','river','water','marker','grass','clover','celandine','fern','flora','poppy','daisy']):continue
            tree=any(s in name for s in ['tree','oak','birch','jacaranda'])
            if isinstance(c,unreal.InstancedStaticMeshComponent) and not tree:continue
            if isinstance(c,unreal.InstancedStaticMeshComponent) and c.get_instance_count()==0:continue
            sources[path]=(mesh,'tree' if tree else 'terrain' if 'terrain' in name else 'structure')
    catalog={}
    for path,(source,kind) in sources.items():
        report['stage']=path;save()
        slots=list(source.get_editor_property('static_materials'))
        trunk=[i for i,m in enumerate(slots) if any(word in (str(m.material_slot_name)+' '+(m.material_interface.get_name() if m.material_interface else '')).lower() for word in ['bark','trunk'])]
        if kind=='tree' and not trunk:
            bounds=source.get_bounds();ext=bounds.box_extent
            entry={'kind':kind,'shape':'capsule','radius_cm':max(8,min(100,min(ext.x,ext.y)*.12)),
                   'half_height_cm':max(40,min(300,ext.z*.65)),'base_z_cm':bounds.origin.z-ext.z,'fallback':True}
            catalog[path]=entry;report['models'][path]=entry;save();continue
        name='NC_'+source.get_name()[:60]+'_'+hashlib.sha256(path.encode()).hexdigest()[:8]
        target='/DAoCVisualBridge/NavigationCollision_v01/'+name
        mesh=A.load_asset(target) if A.does_asset_exist(target) else None
        if mesh is None:
            if kind=='tree':
                read_source=A.load_asset(lods[path]['high_asset']) if path in lods and 'high_asset' in lods[path] else source
                assert read_source,path
                dm=unreal.DynamicMesh();read=unreal.GeometryScriptMeshReadLOD();read.lod_type=unreal.GeometryScriptLODType.RENDER_DATA;read.lod_index=0
                _,result=unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(read_source,dm,unreal.GeometryScriptCopyMeshFromAssetOptions(),read,use_section_materials=False)
                assert 'SUCCESS' in str(result).upper(),(path,str(result))
                for material in range(len(slots)):
                    if material not in trunk:unreal.GeometryScript_Materials.delete_triangles_by_material_id(dm,material)
                mesh=T.duplicate_asset(name,'/DAoCVisualBridge/NavigationCollision_v01',A.load_asset('/Engine/BasicShapes/Cube.Cube'));assert mesh
                options=unreal.GeometryScriptCopyMeshToAssetOptions();options.replace_materials=True;options.new_materials=[m.material_interface for m in slots]
                write=unreal.GeometryScriptMeshWriteLOD();write.lod_index=0
                _,result=unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,mesh,options,write)
                assert 'SUCCESS' in str(result).upper(),(path,str(result))
            else:
                mesh=T.duplicate_asset(name,'/DAoCVisualBridge/NavigationCollision_v01',source);assert mesh
            body=mesh.get_editor_property('body_setup');assert body,path
            body.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            body.set_editor_property('double_sided_geometry',True)
            for section in range(mesh.get_num_sections(0)):E.enable_section_collision(mesh,True,0,section)
            A.save_loaded_asset(mesh,only_if_is_dirty=False)
        assert mesh.get_num_triangles(0)>0,path
        entry={'kind':kind,'shape':'mesh','asset':mesh.get_path_name(),'triangles':mesh.get_num_triangles(0),'trunk_only':kind=='tree'}
        catalog[path]=entry;report['models'][path]=entry;save()
    assert any(row['kind']=='terrain' for row in catalog.values()),'No terrain collision available'
    (R/'collision_catalog.json').write_text(json.dumps({'version':1,'zone_id':207,'origin_m':[1364,130,1263],'models':catalog},indent=2))
    report.update(complete=True,stage='complete');save();print('NAVIGATION_COLLISION_BUILD_PASS',len(catalog))
except Exception:
    report['errors'].append(traceback.format_exc());save();raise
