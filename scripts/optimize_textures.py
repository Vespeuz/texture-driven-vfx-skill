#!/usr/bin/env python3
"""Resize embedded PNG/JPEG images and rename animation clips; retain other buffer views.
For ordinary single-buffer GLBs only. Does not drop frames or change geometry.
"""
import argparse, io, json
from pathlib import Path
from PIL import Image
from glb_utils import read_glb,encode_glb,summarize


def resize(source,dest,resolution=512,animation_name='Animation'):
    g,blob=read_glb(source)
    if resolution<1 or len(g.get('buffers',[]))!=1 or any(v.get('buffer',0)!=0 or 'extensions' in v for v in g.get('bufferViews',[])):
        raise ValueError('Only ordinary, uncompressed single-buffer GLBs supported')
    replacements={}
    for im in g.get('images',[]):
        if 'bufferView' not in im or im.get('mimeType') not in ('image/png','image/jpeg'):raise ValueError('Only embedded PNG/JPEG supported')
        v=g['bufferViews'][im['bufferView']];o=v.get('byteOffset',0);image=Image.open(io.BytesIO(blob[o:o+v['byteLength']])).convert('RGBA')
        # Preserve aspect ratio; normalized UVs remain unchanged.
        scale=min(1,resolution/image.width,resolution/image.height); size=tuple(max(1,round(x*scale)) for x in image.size)
        image=image.resize(size,Image.Resampling.LANCZOS);buf=io.BytesIO();image.save(buf,format='PNG',optimize=True);replacements[im['bufferView']]=buf.getvalue();im['mimeType']='image/png'
    new=bytearray()
    for i,v in enumerate(g['bufferViews']):
        o=v.get('byteOffset',0); data=replacements.get(i,blob[o:o+v['byteLength']]);new.extend(b'\0'*((-len(new))%4));v['byteOffset']=len(new);v['byteLength']=len(data);new.extend(data)
    if animation_name:
        for i,a in enumerate(g.get('animations',[])):a['name']=animation_name if i==0 else f'{animation_name}_{i+1}'
    g['buffers'][0]['byteLength']=len(new);dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(encode_glb(g,bytes(new)));return summarize(g,dest.stat().st_size)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('--out',required=True);p.add_argument('--resolution',type=int,default=512);p.add_argument('--animation-name',default='Animation');a=p.parse_args();print(json.dumps(resize(a.source,a.out,a.resolution,a.animation_name),indent=2))
