"""Display calibration only: retain original palette metadata and saved indices."""
import copy

def linear(x):
    return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4

def srgb(x):
    return x*12.92 if x<=.0031308 else 1.055*x**(1/2.4)-.055

def skin_tint(tone,chroma):
    tint=[linear((1+x)*.5) for x in tone]
    luma=sum(x*w for x,w in zip(tint,[.2126,.7152,.0722]))
    return [luma+(x-luma)*chroma for x in tint]

def calibrate(catalog):
    result=copy.deepcopy(catalog)
    for figure in result['figures'].values():
        if figure['race'] not in ('cel_m','cel_f'):
            continue
        figure['skin_tint_chroma']=.35
        source_colour=figure['swatches']['skin'][0]
        figure['swatches']['skin']=[
            [srgb(linear(base)*tint) for base,tint in zip(source_colour,skin_tint(tone,.35))]
            for tone in figure['meta']['skin_tones']]
    return result
