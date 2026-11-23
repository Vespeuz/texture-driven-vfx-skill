#!/usr/bin/env python3
"""Check VFX GLB structural integrity, budgets and animation portability."""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path
from PIL import Image
from io import BytesIO
from glb_utils import read_glb, summarize

def validate(path, max_tris=200, max_bytes=2097152, max_texture=1024, strict=False, max_draws=9):
    root, blob=read_glb(path)
    stats=summarize(root,Path(path).stat().st_size)
    errors=[]; warnings=[]
    def err(message): errors.append(message)
    def warn(message): warnings.append(message)
    if root.get('asset',{}).get('version')!='2.0': err('Asset must use glTF 2.0')
    if stats['estimated_basepass_drawcalls'] > max_draws: warn(f'Estimated draw-call budget exceeded: {stats["estimated_basepass_drawcalls"]} > {max_draws}')
    if stats['triangles'] > max_tris: warn(f'Triangle budget exceeded: {stats["triangles"]} > {max_tris}')
    if stats['bytes'] > max_bytes: warn(f'File size budget exceeded: {stats["bytes"]} > {max_bytes}')
    if stats['skins']: warn('Contains a skin/armature; prefer animated transforms')
    if stats['animation_channels']<1: err('Missing animation channels')
    if stats['animation_channels']>96: warn('High animation channel count')
    if stats['materials']>3: warn('Many materials increase draw calls')
    if stats['textures']>3: warn('Consider consolidating textures into one RGBA atlas')
    if not root.get('images'): warn('No embedded textures')
    if not any(m.get('alphaMode')=='BLEND' for m in root.get('materials', [])):
        warn('No BLEND material; transparent plane effects may be opaque')
    if root.get('extensionsRequired'):
        warn('Required extensions may reduce importer compatibility: '+str(root['extensionsRequired']))
    for i,v in enumerate(root.get('bufferViews', [])):
        if v.get('buffer',0)!=0: err(f'bufferView {i} references non-GLB buffer')
        if v.get('byteOffset',0)+v['byteLength']>len(blob):err(f'bufferView {i} exceeds BIN chunk')
    accessors=root.get('accessors',[])
    for i,a in enumerate(accessors):
        view_id=a.get('bufferView')
        if view_id is not None and not 0<=view_id<len(root.get('bufferViews',[])):
            err(f'accessor {i} has invalid bufferView')
        if a.get('count',0)<1: err(f'accessor {i} has no data')
    for mi,mesh in enumerate(root.get('meshes',[])):
        if mesh.get('weights') is not None: warn(f'mesh {mi} uses morph weights')
        for prim in mesh.get('primitives',[]):
            if prim.get('targets'): warn(f'mesh {mi} has morph targets')
            if prim.get('material',0)>=len(root.get('materials',[])):
                err(f'mesh {mi} references invalid material')
    nodes=root.get('nodes',[])
    for anim in root.get('animations',[]):
        for ch in anim.get('channels',[]):
            target=ch.get('target',{})
            if target.get('node',-1) not in range(len(nodes)):
                err('Animation channel targets nonexistent node')
                continue
            if target.get('path') not in ('translation','rotation','scale'):
                warn('Non-TRS animation may be unsupported in portable viewers')
            si=ch.get('sampler',-1)
            if not 0<=si<len(anim.get('samplers',[])):
                err('Animation channel references missing sampler')
                continue
            sp=anim['samplers'][si]
            ti=sp['input']
            if not 0<=ti<len(accessors):err('Invalid animation time accessor');continue
            a=accessors[ti]
            if a['componentType']!=5126 or a['type']!='SCALAR':
                err('Animation time accessor must be FLOAT SCALAR')
                continue
            view=root['bufferViews'][a['bufferView']]
            off=view.get('byteOffset',0)+a.get('byteOffset',0)
            times=struct.unpack_from('<'+'f'*a['count'],blob,off)
            if times[0]<0 or any(y<=x for x,y in zip(times,times[1:])):
                err('Nonmonotonic or negative animation keyframe times')
    image_details=[]
    for i,img in enumerate(root.get('images',[])):
        if 'bufferView' not in img:
            warn(f'Image {i} is external; standalone GLB should embed images')
            continue
        vi=img['bufferView']
        if not 0<=vi<len(root.get('bufferViews',[])):
            err(f'Invalid image bufferView {vi}');continue
        view=root['bufferViews'][vi]
        payload=blob[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
        try:
            im=Image.open(BytesIO(payload)); im.load()
            image_details.append({'index':i,'width':im.width,'height':im.height,'mode':im.mode})
            if max(im.size)>max_texture: warn(f'Texture {i} exceeds {max_texture}px: {im.size}')
            if 'A' not in im.getbands(): warn(f'Texture {i} has no alpha channel')
            elif im.getchannel('A').getextrema()==(255,255):warn(f'Texture {i} is fully opaque')
        except Exception as ex:
            err(f'Image {i} could not be decoded: {ex}')
    return {'file':str(path),'metrics':stats,'images':image_details,
            'errors':errors,'warnings':warnings, 'pass':not errors and (not strict or not warnings)}

def main():
    p=argparse.ArgumentParser(description='Validate portable animated GLB VFX')
    p.add_argument('glb')
    p.add_argument('--max-tris',type=int,default=200)
    p.add_argument('--max-bytes',type=int,default=2097152)
    p.add_argument('--max-texture',type=int,default=1024)
    p.add_argument('--max-draws',type=int,default=9, help='Maximum estimated base-pass draw submissions')
    p.add_argument('--strict',action='store_true',help='Treat budget warnings as validation failures')
    p.add_argument('--report',help='Save JSON validation report')
    args=p.parse_args()
    report=validate(args.glb,args.max_tris,args.max_bytes,args.max_texture,args.strict,args.max_draws)
    if args.report:
        Path(args.report).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['pass'] else 1)

if __name__=='__main__':
    main()