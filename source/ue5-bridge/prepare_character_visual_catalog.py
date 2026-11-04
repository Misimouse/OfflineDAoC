import argparse,json
from pathlib import Path

def prepare(catalog,races,original):
    sources={p.stem.lower():p for p in original.glob('*.png')}
    required=set()
    for figure in catalog['figures'].values():
        gltf=json.loads((races/figure['race']/'figure.gltf').read_text(encoding='utf-8'))
        extras={n['name']:gltf['meshes'][n['mesh']].get('extras',{}) for n in gltf['nodes'] if 'mesh' in n}
        head=extras['head'];head_codes=dict(zip(head['targetNames'],head['codes']))
        for name,part in figure['parts'].items():
            source=extras[name];by_code=dict(zip(source.get('codes',[]),source.get('targetNames',[])))
            bindings={target:by_code[code] for target,code in head_codes.items() if 0<code<21 and code in by_code}
            assert set(bindings.values())<=set(part['morphs']),(figure['race'],name,'unimported original morph')
            part['facial_morphs']=bindings
        # Palette buttons use the same source colour as the calibrated material.
        from PIL import Image
        image=Image.open(sources[figure['meta']['faces'][0]['tex'].lower()]).convert('RGB');w,h=image.size
        image=image.crop((w*3//10,h*3//10,w*3//10+w*2//5,h*3//10+h//4)).resize((32,32),Image.Resampling.BILINEAR)
        pixels=list(image.getdata());mean=[sum(p[i] for p in pixels)/(255*len(pixels)) for i in range(3)]
        figure.setdefault('swatches',{})['skin']=[[mean[i]*(1+tone[i])*.5 for i in range(3)] for tone in figure['meta']['skin_tones']]
        required.update(row['tex'].lower() for row in figure['meta'].get('faces',[]))
        required.update(row['tex'].lower() for row in figure['meta'].get('clothes',{}).values() if row.get('tex') and row.get('chan')=='a')
    assert required<=sources.keys(),sorted(required-sources.keys())
    catalog['original_color_sources']={name:str(sources[name].resolve()) for name in sorted(required)}
    return catalog

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Join original facial feature codes to imported hair morphs; no installation writes.')
    p.add_argument('--catalog',required=True,type=Path);p.add_argument('--races',required=True,type=Path);p.add_argument('--original-textures',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();assert a.catalog.resolve()!=a.output.resolve();c=prepare(json.loads(a.catalog.read_text(encoding='utf-8-sig')),a.races,a.original_textures);a.output.write_text(json.dumps(c,indent=2),encoding='utf-8')
