"""Build private runtime LOD copies; the source art mesh and map remain unchanged."""
import json,traceback,hashlib
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parent
ground_only='-BridgeGroundOnly' in unreal.SystemLibrary.get_command_line()
report={'complete':False,'models':{},'errors':[]}
target=ROOT/('Reports/performance/foliage_lods_ground.json' if ground_only else 'Reports/performance/foliage_lods.json')
catalog_target=ROOT/('foliage_lods_ground.json' if ground_only else 'foliage_lods.json')
def write():target.write_text(json.dumps(report,indent=2))
try:
    editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    # Commandlets don't initialize the UI's editor subsystem collection. These
    # stateless asset operations also work with a transient subsystem instance.
    if editor is None:editor=unreal.StaticMeshEditorSubsystem()
    assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/DAoCVisualBridge/PerformanceLOD_v01'],force_rescan=True)
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    rows=json.loads((ROOT/'Reports/performance/foliage_audit.json').read_text())
    selected={}
    for row in rows:
        name=row['mesh'].lower()
        ground=any(s in name for s in ['grass','clover','celandine','fern','flora','poppy','daisy'])
        tree='birch' in name
        if row['count'] and ((ground and row.get('triangles',0)>300) or (tree and not ground_only)):selected[row['mesh']]='tree' if tree else 'ground'
    manifest={}
    for path,kind in selected.items():
        # The grove's Birch was duplicated by apply_ardee_grove.py from this
        # exact source mesh. Reuse its geometry; runtime keeps each instance's
        # current material bindings and scale.
        birch_source='/Game/DAoC/Connacht_v01/Biome_Trial_v01/Models/Joined_v06/BiomeJoined_Birch.BiomeJoined_Birch'
        if kind=='tree' and '/Ardee_Giant_Grove_v01/' in path and birch_source in manifest:
            manifest[path]=dict(manifest[birch_source],shared_geometry_source=birch_source)
            report['models'][path]=manifest[path];write()
            catalog_target.write_text(json.dumps(manifest,indent=2));continue
        name=path.rsplit('/',1)[-1].split('.')[0]+'_'+hashlib.sha256(path.encode()).hexdigest()[:8]
        destination='/DAoCVisualBridge/PerformanceLOD_v01/'+name
        report['stage']=path;write()
        mesh=assets.load_asset(destination) if assets.does_asset_exist(destination) else None
        if mesh is None:
            source=assets.load_asset(path);assert source,path
            mesh=tools.duplicate_asset(name,'/DAoCVisualBridge/PerformanceLOD_v01',source);assert mesh
            percentages=[1,.10,.025,.006,.0015] if kind=='tree' else [1,.25,.05,.01,.002]
            screens=[1,.75,.3,.1,.03] if kind=='tree' else [1,.15,.05,.015,.005]
            settings=[]
            for percent,screen in zip(percentages,screens):
                setting=unreal.StaticMeshReductionSettings();setting.percent_triangles=percent;setting.screen_size=screen;settings.append(setting)
            options=unreal.StaticMeshReductionOptions();options.auto_compute_lod_screen_size=False;options.reduction_settings=settings
            count=editor.set_lods(mesh,options);assert count>=4,(path,count)
            assets.save_loaded_asset(mesh,only_if_is_dirty=False)
        counts=[mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())]
        assert len(counts)>=4 and counts[0]>=counts[-1]>0,(path,counts)
        manifest[path]={'asset':mesh.get_path_name(),'kind':kind,'triangles':counts}
        report['models'][path]=manifest[path];write()
        catalog_target.write_text(json.dumps(manifest,indent=2))
    report.update(complete=True,stage='complete');write();print('BRIDGE_FOLIAGE_LODS_PASS',len(manifest))
except Exception:
    report['errors'].append(traceback.format_exc());write();raise
