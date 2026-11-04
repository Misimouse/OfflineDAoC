"""Import a reversible physique pilot and aligned hands in the isolated character host."""
import copy,hashlib,json,os,re,traceback
from pathlib import Path
import unreal

root=Path(os.environ['DAOC_PHYSIQUE_LAB']).resolve()
project=Path(unreal.Paths.project_dir()).resolve()
assert project==root.parent/'Host'
content=(project/'Plugins/DAoCVisualBridge/Content').resolve()
assert content.is_relative_to(root.parent),'Never import through shared content junctions'
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools=unreal.AssetToolsHelpers.get_asset_tools()
report={'passed':False,'installed':False,'errors':[]}
def load(name):return json.loads((root/'Baseline'/name).read_text(encoding='utf-8-sig'))
try:
    verification=json.loads((root/'physique_source_report.json').read_text())
    assert verification['passed'] and verification['uv_indices_skin_weights_rig_animation_unchanged']
    file=root/'Source/robust_cel_m.glb';sha=hashlib.sha256(file.read_bytes()).hexdigest()
    assert sha==verification['candidate_sha256']
    dest='/DAoCVisualBridge/PhysiqueCelt_v01/cel_m_'+sha[:12]
    paths=assets.list_assets(dest,recursive=True,include_folder=False)
    if not paths:
        task=unreal.AssetImportTask();task.filename=str(file);task.destination_path=dest;task.automated=True;task.save=True;task.replace_existing=False
        tools.import_asset_tasks([task]);paths=assets.list_assets(dest,recursive=True,include_folder=False)
    meshes=[assets.load_asset(p) for p in paths if 'SkeletalMesh' in str(assets.find_asset_data(p).asset_class_path)]
    meshes=[m for m in meshes if isinstance(m,unreal.SkeletalMesh)];assert len(meshes)==1
    mesh=meshes[0];models=load('models.json');equipment=load('equipment_catalog_v01.json');catalog=load('appearance_catalog.json')
    old_path=models['1984']['asset'];definition=equipment['armour']['figures'][old_path];old=unreal.load_asset(old_path)
    before=unreal.SkeletonModifier();after=unreal.SkeletonModifier();assert before.set_skeletal_mesh(old) and after.set_skeletal_mesh(mesh)
    normal=lambda n:re.sub(r'[-_ ]','',str(n)).lower()
    bones={normal(n):n for n in before.get_all_bone_names()};assert len(bones)==len(after.get_all_bone_names())
    for name in after.get_all_bone_names():
        assert normal(name) in bones
        a=before.get_bone_transform(bones[normal(name)],True);b=after.get_bone_transform(name,True)
        assert a.translation.distance(b.translation)<.1,('bone moved',str(name))
        assert abs(sum(getattr(a.rotation,k)*getattr(b.rotation,k) for k in ['x','y','z','w']))>.99999,('bone rotated',str(name))
        assert a.scale3d.distance(b.scale3d)<.001,('bone scaled',str(name))
    skeleton=mesh.get_editor_property('skeleton')
    for source in [old,unreal.load_asset(definition['original_asset'])]:skeleton.add_compatible_skeleton(source.get_editor_property('skeleton'))
    assert assets.save_loaded_asset(skeleton)
    descriptors={s['material']:s for s in definition['sections']};sections=[]
    for index,material in enumerate(mesh.get_editor_property('materials')):
        name=str(material.material_slot_name);assert name in descriptors,name
        sections.append(dict(descriptors[name],index=index))
    assert len(sections)==len(definition['sections'])
    new_definition=dict(definition,asset=mesh.get_path_name(),skeleton=skeleton.get_path_name(),sections=sections,source_sha256=sha)
    del equipment['armour']['figures'][old_path];equipment['armour']['figures'][mesh.get_path_name()]=new_definition
    aliases=[]
    for key,row in models.items():
        if row.get('asset')==old_path:row['asset']=mesh.get_path_name();aliases.append(key)
    texture_file=Path(os.environ['DAOC_ALIGNED_HAND_TEXTURE']).resolve();texture_sha=hashlib.sha256(texture_file.read_bytes()).hexdigest()
    name='T_CeltHands_'+texture_sha[:12];hand_path='/DAoCVisualBridge/HandsAligned_v01/'+name
    hand=unreal.load_asset(hand_path)
    if not hand:
        task=unreal.AssetImportTask();task.filename=str(texture_file);task.destination_path='/DAoCVisualBridge/HandsAligned_v01';task.destination_name=name;task.automated=True;task.save=True;task.replace_existing=False
        tools.import_asset_tasks([task]);hand=unreal.load_asset(hand_path)
    assert hand and hand.get_editor_property('srgb')
    old_hand=catalog['textures']['cthgloves01_ss_cel'];catalog['textures']['cthgloves01_ss_cel']=hand.get_path_name()
    for name,value in [('models_candidate.json',models),('equipment_candidate.json',equipment),('appearance_candidate.json',catalog)]:
        (root/name).write_text(json.dumps(value,indent=2))
    report.update(passed=True,body=mesh.get_path_name(),before=old_path,body_source_sha256=sha,bones_checked=len(bones),sections_checked=len(sections),model_aliases=aliases,hand_before=old_hand,hand_candidate=hand.get_path_name(),hand_source_sha256=texture_sha)
except Exception:report['errors'].append(traceback.format_exc())
(root/'import_report.json').write_text(json.dumps(report,indent=2));assert report['passed'],report['errors']
