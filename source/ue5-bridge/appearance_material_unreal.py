"""Original figure surface math for separate morph-capable head/hair candidates."""
import unreal

def build_appearance_material(root,name,texture,cutout=False):
    assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
    material=unreal.load_asset(root+'/'+name)
    if not material:material=tools.create_asset(name,root,unreal.Material,unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(material)
    material.set_editor_property('two_sided',True)
    if cutout:
        material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
        material.set_editor_property('opacity_mask_clip_value',.5)
    def node(cls,x,y):return lib.create_material_expression(material,cls,x,y)
    def link(source,pin,target,input_name):assert lib.connect_material_expressions(source,pin,target,input_name),(pin,input_name)
    def output(source,pin,property):assert lib.connect_material_property(source,pin,property)
    def sample(param,x,y):
        value=node(unreal.MaterialExpressionTextureSampleParameter2D,x,y)
        value.set_editor_property('parameter_name',param);value.set_editor_property('texture',texture)
        return value
    base=sample('FigureTexture',-1400,0);eye=sample('EyeTexture',-1400,400);tattoo=sample('TattooTexture',-1400,700)
    tint=node(unreal.MaterialExpressionVectorParameter,-1400,-240);tint.set_editor_property('parameter_name','FigureTint');tint.set_editor_property('default_value',unreal.LinearColor(1,1,1,1))
    one=node(unreal.MaterialExpressionConstant,-1200,-400);one.set_editor_property('r',1)
    mask=node(unreal.MaterialExpressionSmoothStep,-1200,180);mask.set_editor_property('const_min',.90);mask.set_editor_property('const_max',.99);link(base,'A',mask,'Value')
    masked=node(unreal.MaterialExpressionLinearInterpolate,-950,-150);link(tint,'RGB',masked,'A');link(one,'',masked,'B');link(mask,'',masked,'Alpha')
    use_mask=node(unreal.MaterialExpressionScalarParameter,-950,-400);use_mask.set_editor_property('parameter_name','UseSkinMask');use_mask.set_editor_property('default_value',0)
    choose=node(unreal.MaterialExpressionLinearInterpolate,-700,-120);link(tint,'RGB',choose,'A');link(masked,'',choose,'B');link(use_mask,'',choose,'Alpha')
    tinted=node(unreal.MaterialExpressionMultiply,-450,0);link(base,'RGB',tinted,'A');link(choose,'',tinted,'B')
    has_eye=node(unreal.MaterialExpressionScalarParameter,-1200,530);has_eye.set_editor_property('parameter_name','HasEye');has_eye.set_editor_property('default_value',0)
    eye_factor=node(unreal.MaterialExpressionLinearInterpolate,-950,400);link(one,'',eye_factor,'A');link(eye,'RGB',eye_factor,'B');link(has_eye,'',eye_factor,'Alpha')
    eye_colour=node(unreal.MaterialExpressionMultiply,-200,0);link(tinted,'',eye_colour,'A');link(eye_factor,'',eye_colour,'B')
    has_tattoo=node(unreal.MaterialExpressionScalarParameter,-1200,980);has_tattoo.set_editor_property('parameter_name','HasTattoo');has_tattoo.set_editor_property('default_value',0)
    tattoo_alpha=node(unreal.MaterialExpressionMultiply,-950,950);link(tattoo,'A',tattoo_alpha,'A');link(has_tattoo,'',tattoo_alpha,'B')
    double=node(unreal.MaterialExpressionMultiply,-950,700);double.set_editor_property('const_b',2);link(tattoo,'RGB',double,'A')
    decal_factor=node(unreal.MaterialExpressionLinearInterpolate,-700,700);link(one,'',decal_factor,'A');link(double,'',decal_factor,'B');link(tattoo_alpha,'',decal_factor,'Alpha')
    result=node(unreal.MaterialExpressionMultiply,50,0);link(eye_colour,'',result,'A');link(decal_factor,'',result,'B');output(result,'',unreal.MaterialProperty.MP_BASE_COLOR)
    if cutout:output(base,'A',unreal.MaterialProperty.MP_OPACITY_MASK)
    for property,value,y in [(unreal.MaterialProperty.MP_ROUGHNESS,.85,200),(unreal.MaterialProperty.MP_SPECULAR,.3,350)]:
        constant=node(unreal.MaterialExpressionConstant,50,y);constant.set_editor_property('r',value);output(constant,'',property)
    lib.set_material_usage(material,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    lib.set_material_usage(material,unreal.MaterialUsage.MATUSAGE_MORPH_TARGETS)
    lib.recompile_material(material);assets.save_loaded_asset(material)
    return material
