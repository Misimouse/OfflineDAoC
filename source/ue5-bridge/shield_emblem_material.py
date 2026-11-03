"""Original shield shader, with checked Unreal material graph connections.

Surface UV0, logo UV1, and pattern UV3 come from the original item mesh.
The caller chooses a new asset name when repairing an installed library.
"""
import unreal

def build_shield_material(root, name="M_OriginalShieldEmblem"):
    assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    lib=unreal.MaterialEditingLibrary
    m=unreal.load_asset(root+'/'+name)
    if not m:
        m=tools.create_asset(name,root,unreal.Material,unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(m)
    m.set_editor_property('two_sided',False)
    def node(cls,x,y):return lib.create_material_expression(m,cls,x,y)
    samples=[]
    for i,(param,uvindex,default) in enumerate([('Surface',0,'Surface_sh_wood01'),('Pattern',3,'Pattern_512'),('Logo',1,'Logo_1')]):
        uv=node(unreal.MaterialExpressionTextureCoordinate,-1100,i*200);uv.set_editor_property('coordinate_index',uvindex)
        tex=node(unreal.MaterialExpressionTextureSampleParameter2D,-900,i*200);tex.set_editor_property('parameter_name',param);tex.set_editor_property('texture',unreal.load_asset(root+'/Textures/'+default));tex.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        assert lib.connect_material_expressions(uv,'',tex,'UVs');samples.append(tex)
    has=node(unreal.MaterialExpressionScalarParameter,-650,550);has.set_editor_property('parameter_name','HasLogo');has.set_editor_property('default_value',0)
    one=node(unreal.MaterialExpressionConstant,-650,430);one.set_editor_property('r',1)
    logo=node(unreal.MaterialExpressionLinearInterpolate,-400,400);assert lib.connect_material_expressions(one,'',logo,'A');assert lib.connect_material_expressions(samples[2],'R',logo,'B');assert lib.connect_material_expressions(has,'',logo,'Alpha')
    mul=node(unreal.MaterialExpressionMultiply,-400,0);assert lib.connect_material_expressions(samples[0],'RGB',mul,'A');assert lib.connect_material_expressions(samples[1],'RGB',mul,'B')
    double=node(unreal.MaterialExpressionMultiply,-200,0);double.set_editor_property('const_b',2);assert lib.connect_material_expressions(mul,'',double,'A')
    product=node(unreal.MaterialExpressionMultiply,0,0);assert lib.connect_material_expressions(double,'',product,'A');assert lib.connect_material_expressions(logo,'',product,'B')
    clamp=node(unreal.MaterialExpressionClamp,200,0);assert lib.connect_material_expressions(product,'',clamp,'')
    linear=node(unreal.MaterialExpressionPower,400,0);linear.set_editor_property('const_exponent',2.2);assert lib.connect_material_expressions(clamp,'',linear,'Base');assert lib.connect_material_property(linear,'',unreal.MaterialProperty.MP_BASE_COLOR)
    rough=node(unreal.MaterialExpressionConstant,400,200);rough.set_editor_property('r',.9);assert lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(m);assets.save_loaded_asset(m)
    return m
