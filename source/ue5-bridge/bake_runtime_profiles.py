"""Bake already-reduced render LODs into private profile meshes. No new simplification."""
import hashlib,json,traceback
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parent
out={'complete':False,'models':{},'errors':[]}
report=ROOT/'Reports/performance/runtime_profiles.json'
def save():report.write_text(json.dumps(out,indent=2))
try:
    A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);T=unreal.AssetToolsHelpers.get_asset_tools()
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/DAoCVisualBridge/PerformanceLOD_v01','/DAoCVisualBridge/RuntimeProfiles_v01'],force_rescan=True)
    catalog=json.loads((ROOT/'foliage_lods.json').read_text());cache={}
    for source,row in catalog.items():
        full=A.load_asset(row['asset']);assert full,row['asset']
        for profile,lod in [('balanced',1 if row['kind']=='tree' else 2),('high',1),('accessible',2 if row['kind']=='tree' else 3)]:
            lod=min(lod,full.get_num_lods()-1);key=(row['asset'],lod)
            if key not in cache:
                name=full.get_name()+'_RenderLOD_'+str(lod)
                path='/DAoCVisualBridge/RuntimeProfiles_v01/'+name
                out['stage']=path;save()
                mesh=A.load_asset(path) if A.does_asset_exist(path) else None
                if mesh is None:
                    dm=unreal.DynamicMesh();read=unreal.GeometryScriptMeshReadLOD();read.lod_type=unreal.GeometryScriptLODType.RENDER_DATA;read.lod_index=lod
                    _,result=unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(full,dm,unreal.GeometryScriptCopyMeshFromAssetOptions(),read,use_section_materials=False)
                    assert 'SUCCESS' in str(result).upper(),(path,str(result))
                    mesh=T.duplicate_asset(name,'/DAoCVisualBridge/RuntimeProfiles_v01',A.load_asset('/Engine/BasicShapes/Cube.Cube'));assert mesh
                    options=unreal.GeometryScriptCopyMeshToAssetOptions();options.replace_materials=True
                    options.new_materials=[m.material_interface for m in full.get_editor_property('static_materials')]
                    write=unreal.GeometryScriptMeshWriteLOD();write.lod_index=0
                    _,result=unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,mesh,options,write)
                    assert 'SUCCESS' in str(result).upper(),(path,str(result))
                    A.save_loaded_asset(mesh,only_if_is_dirty=False)
                assert mesh.get_num_triangles(0)==full.get_num_triangles(lod),(path,mesh.get_num_triangles(0),full.get_num_triangles(lod))
                cache[key]=mesh.get_path_name();out['models'][path]={'triangles':mesh.get_num_triangles(0),'source':row['asset'],'lod':lod};save()
            row[profile+'_asset']=cache[key]
    (ROOT/'foliage_lods.json').write_text(json.dumps(catalog,indent=2))
    out.update(complete=True,stage='complete');save();print('RUNTIME_PROFILES_PASS',len(cache))
except Exception:
    out['errors'].append(traceback.format_exc());save();raise
