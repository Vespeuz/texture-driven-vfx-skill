#!/usr/bin/env python3
"""Build animated, low-poly, texture-driven glTF 2.0 GLBs without Blender.

Requires numpy and Pillow, outputs ONE self-contained GLB + optional atlas/report.
Deliberately avoids skinning, morph targets, UV-scroll shaders, and proprietary extras.
"""
from __future__ import annotations
import argparse
import io
import json
import math
import struct
from pathlib import Path
import numpy as np
from PIL import Image
from atlas import make_atlas, TILES, GRID
from glb_utils import encode_glb, summarize, read_glb
from mesh_shapes import surface, atlas_uv


class BinaryBuilder:
    def __init__(self):
        self.blob=bytearray()
        self.views=[]
        self.accessors=[]

    def add_view(self, data, target=None):
        self.blob.extend(b'\0'*((-len(self.blob)) % 4))
        offset=len(self.blob)
        self.blob.extend(data)
        view={'buffer':0,'byteOffset':offset,'byteLength':len(data)}
        if target is not None:
            view['target']=target
        self.views.append(view)
        return len(self.views)-1

    def add_accessor(self, values, typ, component_type=5126, target=None, bounds=False):
        dtype={5126:np.dtype('<f4'),5123:np.dtype('<u2'),5125:np.dtype('<u4')}[component_type]
        arr=np.asarray(values,dtype=dtype)
        elems={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[typ]
        if arr.size % elems:
            raise ValueError('Invalid accessor shape')
        arr=arr.reshape(-1,elems)
        view=self.add_view(arr.tobytes(order='C'),target)
        obj={'bufferView':view,'byteOffset':0,'componentType':component_type,'count':len(arr),'type':typ}
        if bounds:
            obj['min']=[float(v) if component_type==5126 else int(v) for v in arr.min(axis=0)]
            obj['max']=[float(v) if component_type==5126 else int(v) for v in arr.max(axis=0)]
        self.accessors.append(obj)
        return len(self.accessors)-1


def _quat_xyz(deg):
    rx,ry,rz=(math.radians(float(d))/2 for d in deg)
    x,y,z=math.sin(rx),math.sin(ry),math.sin(rz)
    w,v,u=math.cos(rx),math.cos(ry),math.cos(rz)
    # Euler XYZ using q = qz * qy * qx.
    q=[x*v*u-w*y*z, w*y*u+x*v*z, w*v*z-x*y*u, w*v*u+x*y*z]
    d=math.sqrt(sum(f*f for f in q))
    return [f/d for f in q]


def _quad_vertices(orientation, width, height, planes, uv_rect, atlas_resolution):
    if orientation not in ('vertical','horizontal'):
        raise ValueError(f'orientation must be vertical or horizontal, not {orientation}')
    if not 1 <= planes <= 8:
        raise ValueError('planes must be between 1 and 8')
    if width <= 0 or height <= 0:
        raise ValueError('width and height must be positive')
    u0,v0,u1,v1=uv_rect
    pad=1.5/atlas_resolution
    u0+=pad;v0+=pad;u1-=pad;v1-=pad
    xyz=[];uv=[];indices=[]
    # All quads share the material and atlas; cross-planes have different yaw.
    for p in range(planes):
        yaw=math.pi*p/planes
        c,s=math.cos(yaw),math.sin(yaw)
        base=len(xyz)
        for x,y,u,v in [(-.5,-.5,u0,v1),(.5,-.5,u1,v1),(.5,.5,u1,v0),(-.5,.5,u0,v0)]:
            if orientation=='vertical':
                px=x*width;py=y*height;pz=0
            else:
                px=x*width;py=0;pz=y*height
            xyz.append([px*c+pz*s,py,-px*s+pz*c]);uv.append([u,v])
        indices.extend([base,base+1,base+2,base,base+2,base+3])
    return xyz,uv,indices


def _v3(v,label):
    if not isinstance(v,list) or len(v)!=3:
        raise ValueError(f'{label} must be a three-element array')
    return [float(x) for x in v]


def _frames(layer, duration):
    frames=layer.get('frames',[])
    if len(frames)<2:
        raise ValueError(f"Layer {layer.get('name','?')}: at least 2 animation frames required")
    times=[float(f['t']) for f in frames]
    if times[0]<0 or times[-1]>duration+1e-6 or any(b<=a for a,b in zip(times,times[1:])):
        raise ValueError(f'Layer {layer.get("name")}: times must strictly increase within duration')
    center=_v3(layer.get('center',[0,0,0]),'center')
    position=[]; scales=[]; rotation=[]
    for f in frames:
        off=_v3(f.get('offset',[0,0,0]),'offset')
        position.append([center[i]+off[i] for i in range(3)])
        sc=_v3(f.get('scale',[1,1,1]),'scale')
        if any(x<0 for x in sc):
            raise ValueError('Scale must be nonnegative (use small positive scale to hide)')
        scales.append(sc)
        rotation.append(_quat_xyz(_v3(f.get('rotation_deg',[0,0,0]),'rotation_deg')))
    return times,position,scales,rotation


def create(spec, atlas_image):
    duration=float(spec.get('duration_seconds',2))
    if duration<=0 or duration>60:
        raise ValueError('duration_seconds must be in (0,60]')
    layers=spec.get('layers',[])
    if not 1<=len(layers)<=120:
        raise ValueError('Provide 1-120 layers')
    if atlas_image.width!=atlas_image.height or atlas_image.width%4:
        raise ValueError('Atlas must be square and divisible by 4')
    builder=BinaryBuilder()
    buf=io.BytesIO()
    atlas_image.save(buf,format='PNG',optimize=True)
    png=buf.getvalue()
    img_view=builder.add_view(png)
    gltf={
        'asset':{'version':'2.0','generator':'Texture-Driven VFX Skill v2.0'},
        'extensionsUsed':['KHR_materials_unlit'],
        'scene':0,'scenes':[{'nodes':[]}],
        'nodes':[],'meshes':[],'bufferViews':[], 'buffers':[], 'accessors':[],
        'images':[{'name':'RGBA_VFX_Atlas','mimeType':'image/png','bufferView':img_view}],
        'samplers':[{'magFilter':9729,'minFilter':9729,'wrapS':33071,'wrapT':33071}],
        'textures':[{'sampler':0,'source':0}],
        'materials':[{'name':'Transparent_Unlit_Atlas',
                      'pbrMetallicRoughness':{'baseColorTexture':{'index':0},'metallicFactor':0,'roughnessFactor':1},
                      'alphaMode':'BLEND','doubleSided':True,'extensions':{'KHR_materials_unlit':{}}}],
        'animations':[{'name':spec.get('animation_name','Animation'), 'samplers':[], 'channels':[]}]
    }
    tile_names=spec.get('texture',{}).get('tiles',TILES)
    if not isinstance(tile_names,list) or not 1<=len(tile_names)<=16 or len(set(tile_names))!=len(tile_names):
        raise ValueError('texture.tiles must contain 1-16 unique names')
    names=set()
    for layer in layers:
        name=str(layer.get('name','')).strip()
        if not name or name in names:
            raise ValueError('Every layer needs a distinct nonblank name')
        names.add(name)
        tex=layer.get('texture')
        if tex not in tile_names:
            raise ValueError(f'{name}: tile {tex!r} not in texture.tiles {tile_names}')
        n=tile_names.index(tex)
        rect=((n%GRID)/GRID,(n//GRID)/GRID,(n%GRID+1)/GRID,(n//GRID+1)/GRID)
        orientation=layer.get('orientation','vertical')
        xyz,uv,inds=_quad_vertices(orientation,float(layer.get('width',1)),
                                  float(layer.get('height',1)),int(layer.get('planes',1)),
                                  rect,atlas_image.width)
        if layer.get('shape'):
            xyz,local_uv,inds=surface(layer['shape'],float(layer.get('width',1)),float(layer.get('height',1)),int(layer.get('segments',8)),int(layer.get('planes',2)),float(layer.get('inner',.75)),float(layer.get('turns',1)),float(layer.get('anchor',.5)),orientation)
            pad=1.5/atlas_image.width
            uv=atlas_uv(local_uv,(rect[0]+pad,rect[1]+pad,rect[2]-pad,rect[3]-pad))
        position_accessor=builder.add_accessor(xyz,'VEC3',target=34962,bounds=True)
        uv_accessor=builder.add_accessor(uv,'VEC2',target=34962)
        indices_accessor=builder.add_accessor(inds,'SCALAR',5123,target=34963)
        mesh_index=len(gltf['meshes'])
        gltf['meshes'].append({'name':name+'_plane_mesh','primitives':[
            {'attributes':{'POSITION':position_accessor,'TEXCOORD_0':uv_accessor},
             'indices':indices_accessor,'material':0,'mode':4}]})
        node_index=len(gltf['nodes'])
        times,positions,scales,rotations=_frames(layer,duration)
        gltf['nodes'].append({'name':name,'mesh':mesh_index,
                              'translation':positions[0],'scale':scales[0], 'rotation':rotations[0]})
        gltf['scenes'][0]['nodes'].append(node_index)
        tacc=builder.add_accessor([[t] for t in times],'SCALAR',bounds=True)
        anim=gltf['animations'][0]
        # Optional single native morph target: bend along height by a specified displacement.
        if 'morph_bend' in layer:
            base=np.asarray(xyz,dtype=np.float32); extent=np.ptp(base[:,1]); fraction=(base[:,1]-base[:,1].min())/max(float(extent),1e-6)
            delta=np.zeros_like(base); delta[:,0]=float(layer['morph_bend'])*fraction**2
            ma=builder.add_accessor(delta,'VEC3',target=34962,bounds=True)
            gltf['meshes'][-1]['primitives'][0]['targets']=[{'POSITION':ma}];gltf['meshes'][-1]['weights']=[0.]
            weights=[float(f.get('morph_weight',0)) for f in layer['frames']]
            if any(not 0<=w<=1 for w in weights):raise ValueError('Morph weights must be in [0,1]')
            gltf['nodes'][-1]['weights']=[weights[0]]
            wa=builder.add_accessor(weights,'SCALAR'); si=len(anim['samplers']);anim['samplers'].append({'input':tacc,'output':wa,'interpolation':'LINEAR'});anim['channels'].append({'sampler':si,'target':{'node':node_index,'path':'weights'}})
        for path, vals, typ in [('translation',positions,'VEC3'),('scale',scales,'VEC3'),('rotation',rotations,'VEC4')]:
            if all(np.allclose(vals[0],v,rtol=0,atol=1e-6) for v in vals[1:]):
                continue
            vacc=builder.add_accessor(vals,typ)
            si=len(anim['samplers'])
            anim['samplers'].append({'input':tacc,'output':vacc,'interpolation':'LINEAR'})
            anim['channels'].append({'sampler':si,'target':{'node':node_index,'path':path}})
    if not gltf['animations'][0]['channels']:
        raise ValueError('No animated transforms; at least one layer must move, rotate, or scale')
    gltf['bufferViews']=builder.views
    gltf['accessors']=builder.accessors
    gltf['buffers']=[{'byteLength':len(builder.blob)}]
    return encode_glb(gltf,bytes(builder.blob))


def main():
    p=argparse.ArgumentParser(description='Build a self-contained, rig-free animated texture-VFX GLB')
    p.add_argument('--spec',required=True,help='JSON effect description')
    p.add_argument('--out',required=True,help='GLB output location')
    p.add_argument('--atlas',help='Existing 4x4 RGBA atlas (e.g. AI-generated, see documentation)')
    p.add_argument('--tiles',help='Directory of named RGBA tile PNGs, missing tiles use procedural fallback')
    p.add_argument('--atlas-out',help='Also write generated / provided atlas to a PNG')
    p.add_argument('--report',help='Write JSON generation metrics')
    args=p.parse_args()
    spec=json.loads(Path(args.spec).read_text(encoding='utf-8'))
    ts=spec.get('texture',{})
    if args.atlas and args.tiles:
        p.error('--atlas and --tiles cannot be used together')
    if args.atlas:
        atlas=Image.open(args.atlas).convert('RGBA')
    else:
        atlas=make_atlas(int(ts.get('resolution',512)),ts.get('accent','#35bdf6'),
                         ts.get('core','#f2ffff'),args.tiles,ts.get('tiles'))
    if atlas.getextrema()[3][0]>=255:
        raise ValueError('Atlas has no transparent pixels; provide RGBA with usable alpha')
    binary=create(spec,atlas)
    out=Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(binary)
    if args.atlas_out:
        aout=Path(args.atlas_out)
        aout.parent.mkdir(parents=True, exist_ok=True)
        atlas.save(aout)
    root,_=read_glb(out)
    metrics=summarize(root,out.stat().st_size)
    if args.report:
        Path(args.report).write_text(json.dumps(metrics,indent=2)+'\n')
    print(f'Created {out} | {metrics["triangles"]} triangles | {metrics["animation_channels"]} animation channels | {metrics["bytes"]:,} bytes')


if __name__=='__main__':
    main()
