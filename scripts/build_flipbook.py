#!/usr/bin/env python3
"""Build portable STEP-gated sprite sequences, optionally rigid-batched.
No custom shader or UV animation. Each frame occupies a fixed atlas cell.
"""
import argparse, io, json, math, tempfile
from pathlib import Path
import numpy as np
from PIL import Image
from build_vfx import BinaryBuilder
from glb_utils import encode_glb, read_glb, summarize
from mesh_shapes import surface, atlas_uv
from batch_drawcalls import batch


def build(manifest_path, shape='cross', width=2., height=4., segments=8, planes=2, anchor=0., start=0., animation_name='Animation'):
    path=Path(manifest_path); m=json.loads(path.read_text()); frames=m['frames']; fps=float(m['fps']); n=len(frames)
    if not n or n!=m['frame_count'] or fps<=0 or start<0 or any(abs(float(f['time'])-i/fps)>1e-6 for i,f in enumerate(frames)):
        raise ValueError('Manifest must contain all consecutive frames at declared cadence')
    b=BinaryBuilder(); g={'asset':{'version':'2.0','generator':'Texture-Driven VFX v2.0'},'extensionsUsed':['KHR_materials_unlit'],'scene':0,'scenes':[{'nodes':[]}],'nodes':[],'meshes':[],'images':[],'textures':[],'samplers':[{'magFilter':9729,'minFilter':9729,'wrapS':33071,'wrapT':33071}],'materials':[],'animations':[{'name':animation_name,'samplers':[],'channels':[]}],'extras':{'flipbook':{'fps':fps,'frame_count':n,'start':start,'end':start+n/fps,'method':'STEP-gated fixed UV meshes'}}}
    for i,name in enumerate(m['atlases']):
        im=Image.open(path.parent/name).convert('RGBA'); data=io.BytesIO(); im.save(data,format='PNG',optimize=True)
        g['images'].append({'bufferView':b.add_view(data.getvalue()),'mimeType':'image/png','name':name});g['textures'].append({'source':i,'sampler':0});g['materials'].append({'name':f'Atlas_{i}','alphaMode':'BLEND','doubleSided':True,'pbrMetallicRoughness':{'baseColorTexture':{'index':i},'metallicFactor':0,'roughnessFactor':1},'extensions':{'KHR_materials_unlit':{}}})
    layers=m.get('layers',[{'shape':shape,'width':width,'height':height,'segments':segments,'planes':planes,'anchor':anchor}])
    positions=[];uvs=[];indices=[]
    for l in layers:
        xyz,uv,idx=surface(l.get('shape','cross'),float(l.get('width',width)),float(l.get('height',height)),int(l.get('segments',segments)),int(l.get('planes',planes)),float(l.get('inner',.75)),float(l.get('turns',1)),float(l.get('anchor',anchor)),l.get('orientation','vertical'))
        idx=idx.astype(np.int64)+sum(len(p) for p in positions);positions.append(xyz+np.asarray(l.get('offset',[0,0,0])));uvs.append(uv);indices.extend(idx.tolist())
    if len(indices)==0 or max(indices)>=65536:raise ValueError('Invalid or excessively large combined frame geometry')
    pos=b.add_accessor(np.concatenate(positions),'VEC3',target=34962,bounds=True); inds=b.add_accessor(indices,'SCALAR',5123,34963)
    anim=g['animations'][0]; end=start+n/fps
    def append_node(name,pa,ia,uv,material,on,off):
        tex=b.add_accessor(uv,'VEC2',target=34962); mi=len(g['meshes']); ni=len(g['nodes'])
        g['meshes'].append({'name':name,'primitives':[{'attributes':{'POSITION':pa,'TEXCOORD_0':tex},'indices':ia,'material':material,'mode':4}]})
        times=[0.]; scales=[[1,1,1] if on==0 else [0,0,0]]
        if on>0:times.append(on);scales.append([1,1,1])
        times.append(off);scales.append([0,0,0])
        if off<end-1e-8:times.append(end);scales.append([0,0,0])
        g['nodes'].append({'name':name,'mesh':mi,'scale':scales[0]});g['scenes'][0]['nodes'].append(ni)
        a=b.add_accessor(times,'SCALAR',bounds=True); v=b.add_accessor(scales,'VEC3'); s=len(anim['samplers']);anim['samplers'].append({'input':a,'output':v,'interpolation':'STEP'});anim['channels'].append({'sampler':s,'target':{'node':ni,'path':'scale'}})
    for i,f in enumerate(frames):
        tiles=f.get('layers',[{'rect':f.get('rect')}])
        if len(tiles)!=len(uvs):raise ValueError('Frame tile count does not match geometry layers')
        uv=np.concatenate([atlas_uv(u,t['rect']) for u,t in zip(uvs,tiles)])
        append_node(f'Frame_{i:04}',pos,inds,uv,f['atlas'],start+i/fps,start+(i+1)/fps)
    if m.get('ground'):
        l=m['ground'];p,u,i=surface('plane',float(l.get('width',width)),float(l.get('height',l.get('width',width))),orientation='horizontal');p=p+np.asarray(l.get('offset',[0,0,0]));pa=b.add_accessor(p,'VEC3',target=34962,bounds=True);ia=b.add_accessor(i,'SCALAR',5123,34963)
        on=float(l.get('on',start));off=float(l.get('off',end))
        if not 0<=on<off<=end+1e-8:raise ValueError('Ground on/off times outside clip')
        append_node('Ground_Circle',pa,ia,u,l['atlas'],on,off)
    g.update(bufferViews=b.views,accessors=b.accessors,buffers=[{'byteLength':len(b.blob)}]);return encode_glb(g,bytes(b.blob))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--out',required=True);p.add_argument('--shape',choices=['plane','cross','cylinder','cone','ring','ribbon'],default='cross');p.add_argument('--width',type=float,default=2);p.add_argument('--height',type=float,default=4);p.add_argument('--segments',type=int,default=8);p.add_argument('--planes',type=int,default=2);p.add_argument('--anchor',type=float,default=0);p.add_argument('--start',type=float,default=0);p.add_argument('--batch',action='store_true');p.add_argument('--max-draws',type=int,default=9);p.add_argument('--max-joints',type=int,default=16);p.add_argument('--report');a=p.parse_args()
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    data=build(a.manifest,a.shape,a.width,a.height,a.segments,a.planes,a.anchor,a.start)
    if a.batch:
        with tempfile.TemporaryDirectory() as tmp:
            raw=Path(tmp)/'raw.glb';raw.write_bytes(data);batch(raw,out,a.max_draws,a.max_joints)
    else:out.write_bytes(data)
    root,_=read_glb(out);report=summarize(root,out.stat().st_size);report['flipbook']=root['extras']['flipbook'];report['draws_measured']=False
    if a.report:Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
