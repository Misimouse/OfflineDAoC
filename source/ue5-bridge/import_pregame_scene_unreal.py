"""Import a private copy of the original Hibernian lobby; never save a map."""
import hashlib,json,os,re,struct,traceback
from pathlib import Path
import unreal

root=Path(os.environ['DAOC_BRIDGE_WORKSPACE'])
folder=Path(os.environ.get('DAOC_BRIDGE_PREGAME_SOURCE',str(root/'SourcePregame_v01')))
folder.mkdir(parents=True,exist_ok=True)
source=folder/'hibernia_lobby.glb'
destination='/DAoCVisualBridge/Pregame_v01'
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools=unreal.AssetToolsHelpers.get_asset_tools()
lib=unreal.MaterialEditingLibrary
report={'passed':False,'map_saved':False,'errors':[]}
try:
    raw=source.read_bytes();length=struct.unpack_from('<I',raw,12)[0]
    document=json.loads(raw[20:20+length]);binary=raw[28+length:]
    assert sum(document['accessors'][p['indices']]['count']//3 for m in document['meshes'] for p in m['primitives'])==62798
    assert len(document['meshes'])==1 and len(document['materials'])==28
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([destination],True)
    meshes=[assets.load_asset(p) for p in assets.list_assets(destination,True,False) if isinstance(assets.load_asset(p),unreal.StaticMesh)]
    if not meshes or len(meshes[0].get_editor_property('static_materials'))!=len(document['materials']):
        task=unreal.AssetImportTask();task.filename=str(source);task.destination_path=destination;task.automated=True;task.save=True;task.replace_existing=True
        tools.import_asset_tasks([task])
        meshes=[assets.load_asset(p) for p in assets.list_assets(destination,True,False) if isinstance(assets.load_asset(p),unreal.StaticMesh)]
    assert len(meshes)==1
    textures=[]
    for index,image in enumerate(document['images']):
        name='T_OriginalLobby_%03d'%index;path=destination+'/'+name
        view=document['bufferViews'][image['bufferView']];offset=view.get('byteOffset',0);data=binary[offset:offset+view['byteLength']]
        png=folder/(name+'.png');changed=not png.exists() or png.read_bytes()!=data
        if not assets.does_asset_exist(path) or changed:
            png.write_bytes(data)
            task=unreal.AssetImportTask();task.filename=str(png);task.destination_path=destination;task.destination_name=name;task.automated=True;task.save=True;task.replace_existing=True
            tools.import_asset_tasks([task])
        texture=assets.load_asset(path);assert isinstance(texture,unreal.Texture2D);textures.append(texture)
    material_assets={}
    for definition in document['materials']:
        name=definition['name'];path=destination+'/M_Original_v2_'+name
        material=assets.load_asset(path)
        if material is None:
            material=tools.create_asset('M_Original_v2_'+name,destination,unreal.Material,unreal.MaterialFactoryNew())
            material.set_editor_property('two_sided',True)
            material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
            pbr=definition['pbrMetallicRoughness'];index=document['textures'][pbr['baseColorTexture']['index']]['source']
            sample=lib.create_material_expression(material,unreal.MaterialExpressionTextureSample,-400,0);sample.set_editor_property('texture',textures[index])
            tint=lib.create_material_expression(material,unreal.MaterialExpressionConstant3Vector,-400,160);color=pbr.get('baseColorFactor',[1,1,1,1]);tint.set_editor_property('constant',unreal.LinearColor(*[v*.65 for v in color[:3]],1))
            product=lib.create_material_expression(material,unreal.MaterialExpressionMultiply,-150,0);lib.connect_material_expressions(sample,'RGB',product,'A');lib.connect_material_expressions(tint,'',product,'B');lib.connect_material_property(product,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            if definition.get('alphaMode')=='MASK':
                material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED);material.set_editor_property('opacity_mask_clip_value',definition.get('alphaCutoff',.5));lib.connect_material_property(sample,'A',unreal.MaterialProperty.MP_OPACITY_MASK)
            elif definition.get('alphaMode')=='BLEND':
                material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);lib.connect_material_property(sample,'A',unreal.MaterialProperty.MP_OPACITY)
            lib.recompile_material(material);assets.save_loaded_asset(material)
        material_assets[name]=material
    mesh=meshes[0];slots=mesh.get_editor_property('static_materials');assert len(slots)==len(document['materials'])
    assignments=[]
    for index,slot in enumerate(slots):
        name=str(slot.material_slot_name);match=re.search(r'PGM\d{3}',name);assert match,(index,name)
        key=match.group();mesh.set_material(index,material_assets[key]);assignments.append(key)
    assets.save_loaded_asset(mesh)
    report.update(passed=True,mesh=mesh.get_path_name(),triangles=62798,materials=assignments,textures=len(textures),source_sha256=hashlib.sha256(raw).hexdigest())
    (root/'pregame_catalog.json').write_text(json.dumps({'hibernia_backdrop':mesh.get_path_name()},indent=2),encoding='utf-8')
except Exception:
    report['errors'].append(traceback.format_exc())
(folder/'lobby_import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['passed'],report['errors']
