"""Create original procedural RGBA VFX atlas or pack externally generated textures."""
from __future__ import annotations
from pathlib import Path
from PIL import Image
import numpy as np
import math

TILES = ['beam', 'filament', 'ring', 'rune', 'spark', 'burst', 'glow', 'smoke',
         'slash', 'flame', 'swirl', 'star']
GRID = 4

def _rgb(s):
    s = s.lstrip('#')
    if len(s) != 6 or not all(c in '0123456789abcdefABCDEF' for c in s):
        raise ValueError(f'Expected a 6-digit hex color, got {s!r}')
    return np.array([int(s[i:i+2],16) for i in (0,2,4)], dtype=np.float32)

def _tile(name, size, accent, core, seed=1):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    x = (xx + .5) / size * 2 - 1
    y = (yy + .5) / size * 2 - 1
    r = np.hypot(x,y)
    theta = np.arctan2(y,x)
    rng = np.random.default_rng(seed)
    n = rng.random((size,size)).astype(np.float32)
    v = np.zeros_like(x)
    if name == 'beam':
        center = .09*np.sin(y*7.5) + .04*np.sin(y*18.0+0.9)
        width = .11+.27*np.maximum(0,1-np.abs(y))
        v = np.exp(-np.power(np.abs(x-center)/(width+.001),1.65)*2.3)
        v *= np.clip((y+1.04)*4.8,0,1)*np.clip((1.03-y)*3.5,0,1)
        v *= .78 + .22*np.sin(20*y+5*x)**2
    elif name == 'filament':
        center = .27*np.sin(5*y+0.4)+.08*np.sin(13*y)
        v = np.exp(-((x-center)/.06)**2)*.9
        v += .5*np.exp(-((x+.18*np.cos(6*y)-.15)/.027)**2)
        v *= np.clip((y+1)*5,0,1)*np.clip((1-y)*5,0,1)
    elif name == 'ring':
        v = np.exp(-((r-.72)/.045)**2)*(.7+.3*np.sin(theta*12)**2)
        v += .22*np.exp(-((r-.59)/.05)**2)
    elif name == 'rune':
        v = .45*np.exp(-((r-.72)/.013)**2)+.65*np.exp(-((r-.48)/.018)**2)
        v += .5*np.exp(-((np.sin(theta*4)*.5 + .5)*r-.5)**2/.005)*((r>.52)&(r<.85))
    elif name == 'spark':
        for ox, oy, w in [(-.3,-.15,.8),(.14,.12,1),(.37,-.31,.45)]:
            v += w*np.exp(-((x-ox)/.027)**2-((y-oy)/.40)**2)
    elif name == 'burst':
        aa = np.cos(theta*8)**18
        v = np.clip(aa,0,1)*np.exp(-((r-.49)/.32)**2)*np.clip(r*3,0,1)
        v += .25*np.exp(-(r/.28)**2)
    elif name == 'glow':
        v = .7*np.exp(-(r/.47)**2)+.5*np.exp(-(r/.21)**2)
    elif name == 'smoke':
        centers = [(rng.uniform(-.6,.6),rng.uniform(-.65,.65),rng.uniform(.13,.35)) for _ in range(22)]
        for cx,cy,rr in centers:
            v += .16*np.exp(-((x-cx)**2+(y-cy)**2)/(rr*rr))
        v *= np.clip(1-r,0,1)
    elif name == 'slash':
        arc = r - (.66+.1*np.sin(theta*2))
        mask = ((theta>-.65)&(theta<2.2)).astype(np.float32)
        v = np.exp(-(arc/.034)**2)*mask
        v += .27*np.exp(-((arc-.09)/.11)**2)*mask
    elif name == 'flame':
        center = .2*np.sin(5*y)+.1*np.sin(11*y)
        width = np.clip(.45*(1-y)/2,.02,.42)
        v = np.exp(-((x-center)/(width+.02))**2)
        v *= np.clip((y+1)*4,0,1)*np.clip((1-y)*3.5,0,1)
        v *= (.8 + .2*n)
    elif name == 'swirl':
        target = .21+.10*(theta+math.pi)+.05*np.sin(3*theta)
        v = np.exp(-((r-target)/.035)**2)*np.clip(r,0,1)
        v += .35*np.exp(-((r-(target-.17))/.06)**2)
    elif name == 'star':
        v = np.exp(-(x/.038)**2-(y/.57)**2)+np.exp(-(y/.038)**2-(x/.57)**2)
        v += .65*np.exp(-(r/.20)**2)
    else:
        raise ValueError(f'Unknown tile {name}')
    v = np.clip(v, 0, 1)
    border = np.clip((1-np.maximum(np.abs(x),np.abs(y)))*size/8, 0, 1)
    v *= border
    intensity = np.clip(v*1.25,0,1)
    col = accent[None,None,:]*(1-intensity[...,None]*.58) + core[None,None,:]*(intensity[...,None]*.58)
    rgb = np.clip(col,0,255).astype(np.uint8)
    alpha = np.clip(v*255, 0,255).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb,alpha]), 'RGBA')

def make_atlas(resolution=512, accent='#35bdf6', core='#f2ffff', tile_dir=None, tile_names=None):
    if resolution < 256 or resolution % 4:
        raise ValueError('Atlas resolution must be divisible by 4 and >= 256')
    tile_names = list(tile_names if tile_names is not None else TILES)
    if not 1 <= len(tile_names) <= 16 or len(set(tile_names)) != len(tile_names):
        raise ValueError('Use 1-16 unique texture tile names')
    cell=resolution//GRID
    atlas=Image.new('RGBA',(resolution,resolution),(0,0,0,0))
    for idx, name in enumerate(tile_names):
        file = Path(tile_dir)/f'{name}.png' if tile_dir else None
        if file and file.exists():
            im=Image.open(file).convert('RGBA').resize((cell,cell), Image.Resampling.LANCZOS)
        else:
            if name not in TILES:
                raise ValueError(f'Custom tile {name!r} needs {name}.png in --tiles, or provide a complete --atlas')
            im=_tile(name,cell,_rgb(accent),_rgb(core),idx+14)
        atlas.paste(im, ((idx%GRID)*cell,(idx//GRID)*cell))
    return atlas