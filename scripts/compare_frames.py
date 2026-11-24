#!/usr/bin/env python3
"""Create side-by-side reference/render QA sheet; input pairs must be time and camera matched."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
import numpy as np

def compare(reference,rendered,out,background=(20,24,32)):
    r=sorted(Path(reference).glob('*.png'));s=sorted(Path(rendered).glob('*.png'))
    if not r or len(r)!=len(s):raise ValueError('Provide equal nonempty sets of matched PNG frames')
    w,h=400,280; canvas=Image.new('RGB',(2*w,len(r)*(h+24)),background);d=ImageDraw.Draw(canvas);stats=[]
    for i,(a,b) in enumerate(zip(r,s)):
        images=[]
        for j,p in enumerate((a,b)):
            im=Image.open(p).convert('RGBA');bg=Image.new('RGBA',im.size,background+(255,));bg.alpha_composite(im);im=bg.convert('RGB');images.append(im);thumb=ImageOps.contain(im,(w,h));canvas.paste(thumb,(j*w+(w-thumb.width)//2,i*(h+24)+24+(h-thumb.height)//2));d.text((j*w+8,i*(h+24)+4),('Reference' if j==0 else 'Render')+' | '+p.name,fill='white')
        row={'reference':a.name,'render':b.name}
        if images[0].size==images[1].size:row['mean_abs_rgb_difference']=float(np.abs(np.asarray(images[0],float)-np.asarray(images[1],float)).mean()/255)
        stats.append(row)
    canvas.save(out);return {'pairs':stats,'note':'RGB difference is diagnostic only; artistic fidelity requires manual review. Camera/time alignment not inferred.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reference');p.add_argument('rendered');p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(compare(a.reference,a.rendered,a.out),indent=2))
