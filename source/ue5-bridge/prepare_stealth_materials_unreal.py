"""Build isolated translucent variants; never assign them to meshes or active catalogues."""
import hashlib,json,os,traceback
from pathlib import Path
import unreal

inputs=Path(os.environ['DAOC_STEALTH_INPUTS']).resolve()
output=Path(os.environ['DAOC_STEALTH_OUTPUT']).resolve();output.mkdir(parents=True,exist_ok=True)
signature=hashlib.sha256(inputs.read_bytes()+Path(__file__).read_bytes()).hexdigest()[:16]
library='/DAoCVisualBridge/Stealth_v01/'+signature
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
lib=unreal.MaterialEditingLibrary
report={'passed':False,'installed':False,'library':library,'materials':{},'originals':{},'errors':[]}
baseline={}

def parameters(material):
    result={}
    def value(kind,v):
        if kind=='vector':return [float(v.r),float(v.g),float(v.b),float(v.a)]
        if kind=='texture':return v.get_path_name() if v else None
        return v
    for kind,names,getter in [
        ('scalar',lib.get_scalar_parameter_names,lib.get_material_instance_scalar_parameter_value),
        ('vector',lib.get_vector_parameter_names,lib.get_material_instance_vector_parameter_value),
        ('texture',lib.get_texture_parameter_names,lib.get_material_instance_texture_parameter_value),
        ('switch',lib.get_static_switch_parameter_names,lib.get_material_instance_static_switch_parameter_value)]:
        if isinstance(material,unreal.MaterialInstanceConstant):
            result[kind]={str(n):value(kind,getter(material,n)) for n in names(material) if not str(n).startswith('BridgeStealth')}
    return result

properties=[unreal.MaterialProperty.MP_BASE_COLOR,unreal.MaterialProperty.MP_NORMAL,
    unreal.MaterialProperty.MP_ROUGHNESS,unreal.MaterialProperty.MP_SPECULAR,unreal.MaterialProperty.MP_EMISSIVE_COLOR]

def graph_signature(material):
    return {str(p):[str(type(lib.get_material_property_input_node(material,p))),lib.get_material_property_input_node_output_name(material,p)] for p in properties}

def alpha_mode(source):
    if isinstance(source,unreal.Material):return source.get_editor_property('blend_mode'),float(source.get_editor_property('opacity_mask_clip_value'))
    mode,cutoff=alpha_mode(source.get_editor_property('parent'))
    overrides=source.get_editor_property('base_property_overrides')
    if overrides.get_editor_property('override_blend_mode'):mode=overrides.get_editor_property('blend_mode')
    if overrides.get_editor_property('override_opacity_mask_clip_value'):cutoff=float(overrides.get_editor_property('opacity_mask_clip_value'))
    return mode,cutoff


def variant(source):
    path=source.get_path_name()
    if path in report['materials']:return unreal.load_asset(report['materials'][path])
    assert not path.startswith(library) and isinstance(source,(unreal.Material,unreal.MaterialInstanceConstant))
    parent=None
    if isinstance(source,unreal.MaterialInstanceConstant):parent=variant(source.get_editor_property('parent'))
    mode,cutoff=alpha_mode(source)
    original={'parameters':parameters(source),'effective_blend':str(mode),'mask_cutoff':cutoff}
    if isinstance(source,unreal.Material):
        original.update(blend=str(source.get_editor_property('blend_mode')),graph=graph_signature(source))
    baseline[path]=(source,original)
    name=('MI_' if parent else 'M_')+hashlib.sha256(path.encode()).hexdigest()[:20]
    target=library+'/'+name
    assert not assets.does_asset_exist(target),'Candidate already exists; use a new immutable build identity.'
    clone=assets.duplicate_asset(path,target);assert clone
    if parent:
        lib.set_material_instance_parent(clone,parent)
        overrides=clone.get_editor_property('base_property_overrides')
        overrides.set_editor_property('override_blend_mode',False)
        clone.set_editor_property('base_property_overrides',overrides)
        for key,value in [('BridgeStealthMaskEnabled',float(mode==unreal.BlendMode.BLEND_MASKED)),('BridgeStealthMaskCutoff',cutoff),('BridgeStealthOriginalAlpha',float(mode not in [unreal.BlendMode.BLEND_OPAQUE,unreal.BlendMode.BLEND_MASKED]))]:
            # UE 5.8's setter returns false even after updating the instance.
            # Verify the stored value rather than relying on that return flag.
            lib.set_material_instance_scalar_parameter_value(clone,key,value)
            assert abs(lib.get_material_instance_scalar_parameter_value(clone,key)-value)<1e-6,(path,key)
        lib.update_material_instance(clone)
        actual=parameters(clone)
        if actual!=original['parameters']:
            report['parameter_mismatch']={'source':path,'expected':original['parameters'],'actual':actual}
            raise AssertionError('Original uniform/static parameters changed: '+path)
    else:
        assert not source.get_editor_property('use_material_attributes'),'Material-attribute roots need a dedicated adapter'
        def node(cls,x,y):return lib.create_material_expression(clone,cls,x,y)
        def link(a,p,b,q):assert lib.connect_material_expressions(a,p,b,q)
        def scalar(name,value,x,y):
            n=node(unreal.MaterialExpressionScalarParameter,x,y);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
        one=node(unreal.MaterialExpressionConstant,1450,350);one.set_editor_property('r',1)
        zero=node(unreal.MaterialExpressionConstant,1450,450);zero.set_editor_property('r',0)
        raw_mask=lib.get_material_property_input_node(clone,unreal.MaterialProperty.MP_OPACITY_MASK)
        mask_pin=lib.get_material_property_input_node_output_name(clone,unreal.MaterialProperty.MP_OPACITY_MASK)
        if raw_mask is None:raw_mask=one;mask_pin=''
        threshold=node(unreal.MaterialExpressionIf,1700,200)
        link(raw_mask,mask_pin,threshold,'A')
        limit=scalar('BridgeStealthMaskCutoff',cutoff,1400,100);link(limit,'',threshold,'B')
        pins=lib.get_material_expression_input_names(threshold);assert len(pins)==5,pins
        for name,n in zip(pins[2:],[one,one,zero]):link(n,'',threshold,name)
        enabled=scalar('BridgeStealthMaskEnabled',float(mode==unreal.BlendMode.BLEND_MASKED),1700,650)
        mask=node(unreal.MaterialExpressionLinearInterpolate,1950,200)
        link(one,'',mask,'A');link(threshold,'',mask,'B');link(enabled,'',mask,'Alpha')
        raw_alpha=lib.get_material_property_input_node(clone,unreal.MaterialProperty.MP_OPACITY)
        alpha_pin=lib.get_material_property_input_node_output_name(clone,unreal.MaterialProperty.MP_OPACITY)
        if raw_alpha is None:raw_alpha=one;alpha_pin=''
        use_alpha=scalar('BridgeStealthOriginalAlpha',float(mode not in [unreal.BlendMode.BLEND_OPAQUE,unreal.BlendMode.BLEND_MASKED]),1700,900)
        alpha=node(unreal.MaterialExpressionLinearInterpolate,1950,750)
        link(one,'',alpha,'A');link(raw_alpha,alpha_pin,alpha,'B');link(use_alpha,'',alpha,'Alpha')
        coverage=node(unreal.MaterialExpressionMultiply,2200,300);link(mask,'',coverage,'A');link(alpha,'',coverage,'B')
        control=scalar('BridgeStealthOpacity',.45,2200,650)
        result=node(unreal.MaterialExpressionMultiply,2450,300);link(coverage,'',result,'A');link(control,'',result,'B')
        clone.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
        clone.set_editor_property('translucency_lighting_mode',unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        assert lib.connect_material_property(result,'',unreal.MaterialProperty.MP_OPACITY)
        assert graph_signature(clone)==original['graph'],'Original lighting/colour graph changed'
        lib.recompile_material(clone)
    assert 'BridgeStealthOpacity' in [str(n) for n in lib.get_scalar_parameter_names(clone)]
    assets.save_loaded_asset(clone)
    report['materials'][path]=clone.get_path_name();report['originals'][path]=original
    return clone

try:
    data=json.loads(inputs.read_text(encoding='utf-8-sig'));assert data['materials']
    for path in data['materials']:variant(unreal.load_asset(path))
    for path,(source,original) in baseline.items():
        assert parameters(source)==original['parameters']
        if isinstance(source,unreal.Material):
            assert str(source.get_editor_property('blend_mode'))==original['blend'] and graph_signature(source)==original['graph']
    report['originals_unchanged']=True;report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
(output/'prepared.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['passed'],report['errors']
