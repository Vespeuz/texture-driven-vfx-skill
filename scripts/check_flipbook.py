#!/usr/bin/env python3
"""Verify full-rate STEP flipbook playback data, even after rigid-skin batching."""
import argparse,json
import numpy as np
from glb_utils import read_glb,summarize
from batch_drawcalls import accessor


def check(path):
    g,b=read_glb(path); m=g.get('extras',{}).get('flipbook'); errors=[]
    if not m: raise ValueError('No flipbook manifest metadata')
    n=int(m['frame_count']);fps=float(m['fps']);start=float(m['start']);end=float(m['end']);a=g['animations'][0]; tracks={}
    for c in a['channels']:
        node=g['nodes'][c['target']['node']]; name=node.get('name','')
        if c['target']['path']!='scale' or not name.startswith('Frame_'):continue
        s=a['samplers'][c['sampler']]
        if s.get('interpolation')!='STEP':errors.append(f'{name} is not STEP')
        tracks[int(name.split('_')[1])]=(accessor(g,b,s['input']).ravel(),accessor(g,b,s['output']))
    if set(tracks)!=set(range(n)):errors.append('Frame track count mismatch')
    else:
        for i in range(n):
            t=start+(i+.5)/fps
            visible=[]
            for j,(ts,vs) in tracks.items():
                k=max(0,np.searchsorted(ts,t,side='right')-1)
                if np.max(np.abs(vs[k]))>1e-5:visible.append(j)
            if visible!=[i]:errors.append(f'Expected frame {i} at {t:.6f}, got {visible}')
        for j,(ts,vs) in tracks.items():
            expected=start+j/fps;off=start+(j+1)/fps
            if not np.any(np.isclose(ts,expected,rtol=0,atol=1e-5)) or not np.any(np.isclose(ts,off,rtol=0,atol=1e-5)):errors.append(f'Frame {j} timing missing')
            if np.max(np.abs(vs[max(0,np.searchsorted(ts,end+1e-5,side='right')-1)]))>1e-5:errors.append(f'Frame {j} visible after end')
    return {'pass':not errors,'errors':errors,'frame_count':n,'fps':fps,'duration':end-start,'metrics':summarize(g),'visual_playback_verified':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('glb');a=p.parse_args();r=check(a.glb);print(json.dumps(r,indent=2));raise SystemExit(0 if r['pass'] else 1)
