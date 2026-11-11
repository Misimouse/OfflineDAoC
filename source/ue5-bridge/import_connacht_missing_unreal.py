"""Import only missing Connacht actors into private plugin assets; emit dormant merged catalog."""
import json,os,struct,traceback
from pathlib import Path
import unreal
R=Path(__file__).resolve().parent;D=R/'Reports/connacht_models';S=R/'SourceConnachtModels_v01'
catalog_path=R/'models.json'
candidate_path=R/'models_connacht_candidate_v01.json'
namespace='ConnachtMissing_v01'
expected_ids=None
config_path=os.environ.get('DAOC_CONNACHT_IMPORT_CONFIG')
if config_path:
    config_path=Path(config_path).resolve()
    config=json.loads(config_path.read_text(encoding='utf-8'))
    D=config_path.parent
    S=D/'SourceModels'
    namespace='ConnachtNpcBatch1_v01'
    catalog_path=Path(config['catalog']).resolve()
    candidate_path=D/'candidate_catalog.json'
    expected_ids=config['model_ids']
    assert D.name=='Batch1' and D.parent.name=='ConnachtNpcCoverageLab'
    content=(Path(unreal.Paths.project_plugins_dir()).resolve()/'DAoCVisualBridge/Content'/namespace).resolve()
    assert content.is_relative_to(D) and content.is_dir()
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools()
unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/DAoCVisualBridge/'+namespace],force_rescan=True)
report={'passed':False,'models':{},'errors':[],'map_saved':False,'catalog_activated':False}
def save():(D/'import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
try:
    original=json.loads(catalog_path.read_text(encoding='utf-8-sig'));candidate=dict(original)
    rows=json.loads((S/'exported.json').read_text(encoding='utf-8'))
    assert [row['id'] for row in rows]==expected_ids if expected_ids is not None else len(rows)==5
    for row in rows:
        ident=row['id'];assert ident not in original,'Do not overwrite existing representation'
        raw=Path(row['file']).read_bytes();n=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+n]);expected=[a['name']for a in g.get('animations',[])if a['name']!='RESET']
        assert expected and g.get('skins') and g.get('images')
        destination='/DAoCVisualBridge/'+namespace+'/Model_'+ident
        paths=assets.list_assets(destination,recursive=True,include_folder=False)
        if not paths:
            task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=destination;task.automated=True;task.save=True;task.replace_existing=False
            tools.import_asset_tasks([task]);paths=assets.list_assets(destination,recursive=True,include_folder=False)
        loaded=[assets.load_asset(p)for p in paths];meshes=[a for a in loaded if isinstance(a,unreal.SkeletalMesh)];clips=[a for a in loaded if isinstance(a,unreal.AnimSequence)]
        assert len(meshes)==1,(ident,'mesh count',len(meshes))
        mesh=meshes[0];skeleton=mesh.get_editor_property('skeleton');mapped={}
        for clip in expected:
            choices=[a for a in clips if a.get_name()in[clip,f'model_{ident}{clip}',f'model_{ident}_{clip}']]
            assert len(choices)==1,(ident,'animation mapping',clip)
            a=choices[0];assert a.get_editor_property('skeleton')==skeleton and a.get_play_length()>0
            mapped[clip]=a.get_path_name()
        materials=mesh.get_editor_property('materials');textures=[a for a in loaded if isinstance(a,unreal.Texture2D)]
        assert materials and all(m.material_interface for m in materials) and textures,(ident,'materials/textures')
        entry=dict(asset=mesh.get_path_name(),type='skeletal',scale=row['scale'],yaw_offset=-90,name=row['name'],**mapped)
        assert 'idle'in entry,(ident,'idle')
        candidate[ident]=entry
        report['models'][ident]={'entry':entry,'clips':len(mapped),'source_clips':len(expected),'source_meshes':len(g['meshes']),'material_count':len(materials),'textures':[a.get_path_name()for a in textures],'skeleton':skeleton.get_path_name()};save()
    assert all(candidate[k]==v for k,v in original.items())
    candidate_path.write_text(json.dumps(candidate,indent=2),encoding='utf-8')
    report.update(passed=True,original_entries=len(original),candidate_entries=len(candidate),existing_entries_unchanged=True);save()
except Exception:
    report['errors'].append(traceback.format_exc());save();raise
