#!/usr/bin/env python3
"""Reduce draw submissions for standard texture-plane GLB animation using rigid skinning.

Transforms individual sprite meshes into one-joint-influenced rigid sprites
within merged per-material mesh primitives. Preserves original TRS animation,
UVs, geometry, embedded textures, and material settings. No shader extensions.

Limits: exactly one triangle-list mesh primitive per root scene node;
no prior skin, morph target, node hierarchy, or matrix-only transform.
Requires a runtime that supports core glTF skinning animations.
"""
from __future__ import annotations
import argparse, copy, json, sys
from pathlib import Path
import numpy as np
from glb_utils import read_glb, encode_glb, summarize
from build_vfx import BinaryBuilder

def accessor(root, blob, idx):
    a=root['accessors'][idx]; v=root['bufferViews'][a['bufferView']]
    dt={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}[a['componentType']]
    dim={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    offset=v.get('byteOffset',0)+a.get('byteOffset',0)
    stride=v.get('byteStride',np.dtype(dt).itemsize*dim)
    if stride==np.dtype(dt).itemsize*dim:
        return np.frombuffer(blob,dtype=dt,count=a['count']*dim,offset=offset).reshape(-1,dim).copy()
    return np.array([np.frombuffer(blob,dtype=dt,count=dim,offset=offset+i*stride) for i in range(a['count'])])

def batch(input_path,output_path,max_draws=9,max_joints=16,report_path=None):
    root,srcbin=read_glb(input_path)
    if root.get('skins'):
        raise ValueError('Input already contains skins; this utility batches only simple unskinned sprite models')
    if len(root.get('scenes',[]))!=1:
        raise ValueError('Only a single source scene is supported')
    scene_nodes=root['scenes'][0]['nodes']
    if set(scene_nodes)!=set(range(len(root.get('nodes',[])))):
        raise ValueError('All source nodes must be top-level objects (no nested hierarchy)')
    entries=[]
    for ni,node in enumerate(root['nodes']):
        if 'mesh' not in node or 'children' in node or 'matrix' in node:
            raise ValueError(f'Node {ni} must be a mesh-only TRS node without children')
        mesh=root['meshes'][node['mesh']]
        if len(mesh['primitives'])!=1:
            raise ValueError(f'Node {ni} mesh must have exactly one primitive')
        prim=mesh['primitives'][0]
        if prim.get('mode',4)!=4 or prim.get('targets') or 'indices' not in prim:
            raise ValueError(f'Node {ni} requires indexed triangle geometry, no morphs')
        if set(prim['attributes'])!={'POSITION','TEXCOORD_0'}:
            raise ValueError(f'Node {ni} requires POSITION and TEXCOORD_0 only')
        entries.append((ni,prim))
    if not entries:raise ValueError('No source meshes')
    mats={}
    for ni,pr in entries:mats.setdefault(pr.get('material',0),[]).append((ni,pr))
    groups=[]
    for mat,items in mats.items():
        for start in range(0,len(items),max_joints):
            groups.append((mat,items[start:start+max_joints]))
    if len(groups)>max_draws:
        raise ValueError(f'Requires {len(groups)} draw groups, above target {max_draws}; raise --max-joints or reduce sprites')
    r=copy.deepcopy(root)
    r['meshes']=[];r['skins']=[]
    for node in r['nodes']:node.pop('mesh',None)
    joint_root=len(r['nodes'])
    r['nodes'].append({'name':'BATCHED_JOINT_ROOT','children':list(range(len(entries)))})
    r['scenes'][0]['nodes']=[joint_root]
    accbase=len(r['accessors']);viewbase=len(r['bufferViews'])
    builder=BinaryBuilder()
    group_report=[]
    for gi,(material,items) in enumerate(groups):
        verts=[];uvs=[];ids=[];weights=[];indices=[];joints=[];ibms=[]
        for jid,(nodeid,prim) in enumerate(items):
            node=root['nodes'][nodeid]
            rest=np.array(node.get('translation',[0.,0.,0.]),dtype='<f4')
            xyz=accessor(root,srcbin,prim['attributes']['POSITION']).astype('<f4')
            uv=accessor(root,srcbin,prim['attributes']['TEXCOORD_0']).astype('<f4')
            ix=accessor(root,srcbin,prim['indices']).flatten().astype('int64')
            assert ix.max()+len(verts)<65536, 'Combined batch exceeds uint16 indices'
            indices.extend((ix+len(verts)).tolist())
            verts.extend((xyz+rest).tolist());uvs.extend(uv.tolist())
            ids.extend([[jid,0,0,0]]*len(xyz));weights.extend([[1.,0,0,0]]*len(xyz))
            joints.append(nodeid)
            inv=np.eye(4,dtype='<f4');inv[:3,3]=-rest
            ibms.append(inv.T.flatten())
        def acc(values,typ,comp=5126,target=None,bounds=False):
            return accbase+builder.add_accessor(values,typ,comp,target,bounds)
        pa=acc(verts,'VEC3',target=34962,bounds=True)
        ta=acc(uvs,'VEC2',target=34962)
        ja=acc(ids,'VEC4',5123,34962)
        wa=acc(weights,'VEC4',target=34962)
        ia=acc(indices,'SCALAR',5123,34963)
        iv=builder.add_view(np.asarray(ibms,dtype='<f4').tobytes())
        ibacc=accbase+len(builder.accessors)
        builder.accessors.append({'bufferView':iv,'byteOffset':0,'componentType':5126,'count':len(joints),'type':'MAT4'})
        mid=len(r['meshes'])
        r['meshes'].append({'name':f'Batched_Material_{material}_{gi:02d}',
             'primitives':[{'attributes':{'POSITION':pa,'TEXCOORD_0':ta,'JOINTS_0':ja,'WEIGHTS_0':wa},
                            'indices':ia,'material':material,'mode':4}]})
        skinidx=len(r['skins'])
        r['skins'].append({'name':f'RigidSprites_{gi:02d}','inverseBindMatrices':ibacc,
                           'skeleton':joint_root,'joints':joints})
        rendernode=len(r['nodes'])
        r['nodes'].append({'name':f'Batched_Draw_{gi:02d}','mesh':mid,'skin':skinidx})
        r['scenes'][0]['nodes'].append(rendernode)
        group_report.append({'material':material,'sprite_count':len(joints),
                             'triangles':len(indices)//3,'joints':len(joints)})
    for view in builder.views:
        vv=copy.deepcopy(view)
        vv['byteOffset']=vv.get('byteOffset',0)+len(srcbin)
        r['bufferViews'].append(vv)
    for accessor_ in builder.accessors:
        aa=copy.deepcopy(accessor_);aa['bufferView']+=viewbase;r['accessors'].append(aa)
    newbin=srcbin+bytes(builder.blob)
    r['buffers'][0]['byteLength']=len(newbin)
    r['asset']['generator']=r['asset'].get('generator','')+' / Texture-Driven VFX Rigid Batcher'
    dest=Path(output_path);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(encode_glb(r,newbin))
    metrics=summarize(r,dest.stat().st_size)
    metrics.update({'estimated_basepass_drawcalls':len(groups), 'draw_group_details':group_report,
        'caveats':['Base-pass estimate, not GPU benchmark',
                    'Core glTF skinning required for playback',
                    'Transparent sorting now at grouped primitive granularity']})
    if report_path:Path(report_path).write_text(json.dumps(metrics,indent=2))
    return metrics

def main():
    p=argparse.ArgumentParser(description='Batch texture-animated GLB sprites to reduce draw submissions')
    p.add_argument('source');p.add_argument('--out',required=True)
    p.add_argument('--max-draws',type=int,default=9)
    p.add_argument('--max-joints',type=int,default=16)
    p.add_argument('--report')
    args=p.parse_args()
    if args.max_draws<1 or args.max_joints<1 or args.max_joints>64:
        p.error('max-draws must be positive; max-joints must be 1–64')
    print(json.dumps(batch(args.source,args.out,args.max_draws,args.max_joints,args.report),indent=2))

if __name__=='__main__':main()