"""Low-poly, Y-up VFX surfaces with normalized local UV coordinates."""
import math
import numpy as np


def surface(shape='cross', width=1., height=1., segments=8, planes=2, inner=.75, turns=1., anchor=0., orientation='vertical'):
    if width<=0 or height<=0 or not 3<=segments<=128 or not 1<=planes<=8 or not 0<inner<1:
        raise ValueError('Invalid mesh dimensions or segments')
    p=[]; uv=[]; idx=[]
    def strip(a,b):
        k=len(p); p.extend(a); uv.extend(b)
        for i in range(0,len(a)-2,2): idx.extend([k+i,k+i+1,k+i+2,k+i+1,k+i+3,k+i+2])
    if shape in ('plane','cross'):
        for i in range(1 if shape=='plane' else planes):
            t=math.pi*i/planes; x=width/2*math.cos(t); z=width/2*math.sin(t)
            if orientation=='horizontal':
                pts=[[-width/2,0,-height/2],[width/2,0,-height/2],[-width/2,0,height/2],[width/2,0,height/2]]
            else: pts=[[-x,-anchor*height,-z],[x,-anchor*height,z],[-x,(1-anchor)*height,-z],[x,(1-anchor)*height,z]]
            strip(pts,[(0,1),(1,1),(0,0),(1,0)])
    elif shape in ('cylinder','cone','ring','ribbon'):
        a=[]; b=[]
        for i in range(segments+1):
            f=i/segments; t=2*math.pi*f*(turns if shape=='ribbon' else 1); c,s=math.cos(t),math.sin(t); r=width/2
            if shape=='ring': lo=[r*inner*c,0,r*inner*s]; hi=[r*c,0,r*s]
            elif shape=='ribbon': lo=[r*c,height*f-anchor*height-width*.12,r*s]; hi=[r*c,height*f-anchor*height+width*.12,r*s]
            else: lo=[r*c,-anchor*height,r*s]; rr=r*(.06 if shape=='cone' else 1); hi=[rr*c,(1-anchor)*height,rr*s]
            a.extend([lo,hi]); b.extend([(f,1),(f,0)])
        strip(a,b)
    else: raise ValueError('Unknown shape: '+shape)
    return np.asarray(p,dtype=np.float32),np.asarray(uv,dtype=np.float32),np.asarray(idx,dtype=np.uint16)


def atlas_uv(uv, rect):
    u,v,w,h=rect
    return np.asarray(uv)*[w-u,h-v]+[u,v]
