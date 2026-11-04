"""Measure global skin colour calibration without editing generated atlas pixels."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image

def linear(x):return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)

def measure(original,generated,expected_aspect):
    source=np.asarray(Image.open(original).convert('RGBA'),dtype=float)/255
    image=np.asarray(Image.open(generated).convert('RGB'),dtype=float)/255
    h,w=source.shape[:2];gh,gw=image.shape[:2]
    assert abs(gw/gh-expected_aspect)<.001,'Atlas aspect ratio changed'
    # Bilinear samples at corresponding normalized UV positions, for statistics
    # only. The generated PNG remains byte-identical to the image tool output.
    xs=(np.arange(w)+.5)*gw/w-.5;ys=(np.arange(h)+.5)*gh/h-.5
    x0=np.clip(np.floor(xs).astype(int),0,gw-1);x1=np.minimum(x0+1,gw-1);fx=(xs-np.floor(xs))[None,:,None]
    y0=np.clip(np.floor(ys).astype(int),0,gh-1);y1=np.minimum(y0+1,gh-1);fy=(ys-np.floor(ys))[:,None,None]
    sampled=(image[y0[:,None],x0]*(1-fx)+image[y0[:,None],x1]*fx)*(1-fy)+(image[y1[:,None],x0]*(1-fx)+image[y1[:,None],x1]*fx)*fy
    t=np.clip((source[:,:,3]-.90)/.09,0,1);weight=1-t*t*(3-2*t);assert weight.sum()>100
    target=(linear(source[:,:,:3])*weight[:,:,None]).sum(axis=(0,1))/weight.sum()
    current=(linear(sampled)*weight[:,:,None]).sum(axis=(0,1))/weight.sum()
    scale=target/current;assert np.isfinite(scale).all() and (scale>.4).all() and (scale<2.5).all()
    return {'source':str(generated.resolve()),'sha256':hashlib.sha256(generated.read_bytes()).hexdigest(),'source_dimensions':[gw,gh],'original_dimensions':[w,h],'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'skin_colour_scale':scale.tolist(),'target_skin_mean_linear':target.tolist(),'generated_skin_mean_linear':current.tolist()}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--original-textures',type=Path,required=True);p.add_argument('--arms',type=Path,required=True);p.add_argument('--hands',type=Path,required=True);p.add_argument('--arms-normal',type=Path);p.add_argument('--hands-normal',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result={'passed':True,'generated_pixels_modified':False,'textures':{}}
    for name,file,aspect,size in [('ctharms01_ss_bri',a.arms,.5,[1024,2048]),('cthgloves01_ss_cel',a.hands,2,[2048,1024])]:
        result['textures'][name]=dict(measure(a.original_textures/(name+'.png'),file,aspect),build_dimensions=size)
        normal=a.arms_normal if name.startswith('ctharms') else a.hands_normal
        if normal:
            data=np.asarray(Image.open(normal).convert('RGB'));assert abs(data.shape[1]/data.shape[0]-aspect)<.001
            mean=data.mean(axis=(0,1));assert 100<mean[0]<155 and 100<mean[1]<155 and mean[2]>220,'Invalid normal-map encoding'
            result['textures'][name]['normal']={'source':str(normal.resolve()),'sha256':hashlib.sha256(normal.read_bytes()).hexdigest(),'strength':.5,'mean_encoded_rgb':mean.tolist()}
    a.output.write_text(json.dumps(result,indent=2));print('SKIN_COLOUR_CALIBRATION_PASS', {k:v['skin_colour_scale'] for k,v in result['textures'].items()})
