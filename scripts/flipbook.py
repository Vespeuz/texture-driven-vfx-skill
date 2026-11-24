#!/usr/bin/env python3
"""Extract authorized video frames or pack original RGBA frames; preserve cadence.
No automatic source-art rights clearance. Background estimation assumes a known plate.
"""
import argparse, json, math, subprocess, tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter


def matte(image, background, threshold=5, feather=12):
    """Approximate straight alpha by RGB difference from a clean background plate.
    Single-view additive effects are underdetermined; check against multiple backgrounds.
    """
    rgb=np.asarray(image.convert('RGB'),dtype=np.float32)/255
    bg=np.asarray(background.convert('RGB').resize(image.size),dtype=np.float32)/255
    # Minimum alpha that permits RGB foreground in [0,1] under source-over.
    d=rgb-bg
    a=np.max(np.where(d>=0,d/np.maximum(1-bg,1e-5),-d/np.maximum(bg,1e-5)),axis=-1)
    delta=np.max(np.abs(d),axis=-1)*255
    gate=np.clip((delta-threshold)/max(feather,1e-5),0,1)
    a=np.clip(a*gate,0,1)
    fg=np.clip(bg+d/np.maximum(a[...,None],1e-5),0,1)
    out=np.concatenate([fg,a[...,None]],axis=-1)
    out[a==0,:3]=0
    return Image.fromarray(np.uint8(np.rint(out*255)),'RGBA')


def padded(im, size, padding=4, edge=3):
    """Fit a full frame into a transparent cell, maintaining common framing."""
    w,h=size
    if min(w,h)<=padding*2+2: raise ValueError('Cell too small for padding')
    im=im.convert('RGBA').copy(); im.thumbnail((w-2*padding,h-2*padding),Image.Resampling.LANCZOS)
    a=np.asarray(im,dtype=np.float32).copy()
    if edge:
        yy,xx=np.indices(a.shape[:2]); dist=np.minimum.reduce([xx,yy,a.shape[1]-1-xx,a.shape[0]-1-yy]); a[:,:,3]*=np.clip(dist/edge,0,1)
    a[a[:,:,3]==0,:3]=0
    out=Image.new('RGBA',(w,h)); out.paste(Image.fromarray(np.uint8(a)),((w-im.width)//2,(h-im.height)//2))
    return out


def pack(frames,out,fps=30,resolution=512,columns=2,rows=4,padding=4,edge=3):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if not frames or not 0<fps<=240 or resolution<32 or min(columns,rows)<1: raise ValueError('Invalid frame/atlas settings')
    if len({im.size for im in frames})!=1: raise ValueError('Frames must have common dimensions; do not crop independently')
    cw,ch=resolution//columns,resolution//rows
    capacity=columns*rows; entries=[]; names=[]
    for first in range(0,len(frames),capacity):
        atlas=Image.new('RGBA',(resolution,resolution)); ai=len(names); name=f'atlas_{ai:03}.png';names.append(name)
        for j,im in enumerate(frames[first:first+capacity]):
            x=(j%columns)*cw;y=(j//columns)*ch
            atlas.paste(padded(im,(cw,ch),padding,edge),(x,y))
            entries.append({'atlas':ai,'rect':[(x+.5)/resolution,(y+.5)/resolution,(x+cw-.5)/resolution,(y+ch-.5)/resolution],'time':(first+j)/fps})
        atlas.save(out/name,optimize=True)
    manifest={'fps':fps,'frame_count':len(frames),'duration':len(frames)/fps,'resolution':resolution,'atlases':names,'frames':entries,'cell_size':[cw,ch],'source_size':list(frames[0].size),'padding':padding}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n'); return manifest



def pack_layers(plan_path,out,fps=30,resolution=512,columns=2,rows=4,padding=4,edge=3):
    """Pack synchronized frame layers into distinct subrects of each atlas cell."""
    plan_path=Path(plan_path); plan=json.loads(plan_path.read_text()); layers=plan['layers']; sources=[]
    if not layers or not 0<fps<=240 or min(columns,rows)<1 or resolution<32:raise ValueError('Invalid layered atlas settings')
    for l in layers:
        files=sorted((plan_path.parent/l['directory']).glob('*.png'))
        if not files:raise ValueError('Missing PNG sequence '+l['directory'])
        images=[Image.open(f).convert('RGBA') for f in files]
        if len({im.size for im in images})!=1:raise ValueError('Layer frames must have common dimensions')
        sources.append(images)
    n=len(sources[0]);cw,ch=resolution//columns,resolution//rows; cap=columns*rows
    if any(len(x)!=n for x in sources):raise ValueError('All layers must have the same frame count; use transparent frames for inactive periods')
    rects=[]
    for l in layers:
        u,v,w,h=l['cell_rect']; rect=(round(u*cw),round(v*ch),round(w*cw),round(h*ch))
        if not (0<=rect[0]<rect[2]<=cw and 0<=rect[1]<rect[3]<=ch):raise ValueError('Layer cell_rect must be inside the unit cell')
        if any(rect[0]<r[2] and rect[2]>r[0] and rect[1]<r[3] and rect[3]>r[1] for r in rects):raise ValueError('Layer cell rectangles overlap')
        rects.append(rect)
    out=Path(out);out.mkdir(parents=True,exist_ok=True); names=[]; entries=[]
    for first in range(0,n,cap):
        atlas=Image.new('RGBA',(resolution,resolution));ai=len(names);name=f'atlas_{ai:03}.png';names.append(name)
        for j in range(min(cap,n-first)):
            x=(j%columns)*cw;y=(j//columns)*ch; tiles=[]
            for l,src,r in zip(layers,sources,rects):
                x0,y0,x1,y1=r;cell=padded(src[first+j],(x1-x0,y1-y0),int(l.get('padding',padding)),int(l.get('edge',edge)))
                atlas.paste(cell,(x+x0,y+y0));tiles.append({'rect':[(x+x0+.5)/resolution,(y+y0+.5)/resolution,(x+x1-.5)/resolution,(y+y1-.5)/resolution]})
            entries.append({'atlas':ai,'time':(first+j)/fps,'layers':tiles})
        atlas.save(out/name,optimize=True)
    m={'fps':fps,'frame_count':n,'duration':n/fps,'resolution':resolution,'atlases':names,'frames':entries,'cell_size':[cw,ch],'layers':[{k:v for k,v in l.items() if k not in ('directory','cell_rect','padding','edge')} for l in layers]}
    if plan.get('ground'):
        ground=dict(plan['ground']);im=Image.open(plan_path.parent/ground.pop('image')).convert('RGBA');im=padded(im,(resolution,resolution),padding,edge);im.save(out/'ground.png',optimize=True);ground['atlas']=len(names);names.append('ground.png');m['ground']=ground
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');return m


def extract(video,start,duration,fps,crop=None):
    if duration<=0 or start<0: raise ValueError('Invalid time range')
    with tempfile.TemporaryDirectory() as tmp:
        vf=f'fps={fps}'+(f',crop={crop}' if crop else '')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-ss',str(start),'-i',str(video),'-t',str(duration),'-vf',vf,'-threads','1',str(Path(tmp)/'%06d.png')],check=True)
        return [Image.open(p).convert('RGBA') for p in sorted(Path(tmp).glob('*.png'))]


def bake(image, count, kind='scroll', seed=7):
    """Bake texture motion to RGBA frames. No runtime shader required."""
    if count<2:raise ValueError('Need at least two frames')
    a=np.asarray(image.convert('RGBA')); h,w=a.shape[:2]; yy,xx=np.indices((h,w)); frames=[]
    rng=np.random.default_rng(seed);noise=rng.random((h,w)); noise=np.asarray(Image.fromarray(np.uint8(noise*255)).filter(ImageFilter.GaussianBlur(3)),dtype=float)/255
    for i in range(count):
        f=i/(count-1)
        if kind=='scroll': b=np.roll(a,round(f*h),axis=0)
        elif kind=='distort': b=a[yy,(xx+np.rint(w*.04*np.sin(yy/h*math.tau*2+f*math.tau)).astype(int))%w]
        elif kind=='erode':
            b=a.copy(); b[:,:,3]=np.uint8(b[:,:,3]*np.clip((noise-f*1.2+.2)*8,0,1))
        else: raise ValueError('Unknown bake kind')
        frames.append(Image.fromarray(b,'RGBA'))
    return frames


def main():
    p=argparse.ArgumentParser(description=__doc__); s=p.add_subparsers(dest='mode',required=True)
    for name in ('video','images','bake','layers'):
        q=s.add_parser(name);q.add_argument('source');q.add_argument('--out',required=True);q.add_argument('--fps',type=float,default=30);q.add_argument('--resolution',type=int,default=512);q.add_argument('--columns',type=int,default=2);q.add_argument('--rows',type=int,default=4);q.add_argument('--padding',type=int,default=4);q.add_argument('--edge',type=int,default=3)
        if name=='video':
            q.add_argument('--authorized',action='store_true',required=True);q.add_argument('--start',type=float,default=0);q.add_argument('--duration',type=float,required=True);q.add_argument('--crop',help='FFmpeg w:h:x:y');q.add_argument('--background',required=True,help='Clean background PNG matching the crop')
        if name=='bake':q.add_argument('--count',type=int,default=64);q.add_argument('--kind',choices=['scroll','distort','erode'],default='scroll')
    a=p.parse_args()
    if a.mode=='video':
        frames=extract(a.source,a.start,a.duration,a.fps,a.crop);bg=Image.open(a.background);frames=[matte(im,bg) for im in frames]
    elif a.mode=='images':frames=[Image.open(f).convert('RGBA') for f in sorted(Path(a.source).glob('*.png'))]
    elif a.mode=='layers':
        print(json.dumps(pack_layers(a.source,a.out,a.fps,a.resolution,a.columns,a.rows,a.padding,a.edge),indent=2));return
    else:frames=bake(Image.open(a.source),a.count,a.kind)
    print(json.dumps(pack(frames,a.out,a.fps,a.resolution,a.columns,a.rows,a.padding,a.edge),indent=2))

if __name__=='__main__':main()
