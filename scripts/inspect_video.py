#!/usr/bin/env python3
"""Extract a small storyboard from video using optional FFmpeg / FFprobe binaries."""
from __future__ import annotations
import argparse
import io
import json
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

def probe(path):
    try:
        payload=subprocess.check_output(['ffprobe','-v','error','-show_entries',
                                         'format=duration:stream=width,height,avg_frame_rate',
                                         '-of','json',str(path)],stderr=subprocess.STDOUT)
        return json.loads(payload)
    except (OSError,subprocess.CalledProcessError) as e:
        raise RuntimeError('FFprobe is required for video inspection') from e

def frame(path,t,width):
    cmd=['ffmpeg','-nostdin','-v','error','-ss',str(t),'-i',str(path),
         '-frames:v','1','-vf',f'scale={width}:-2','-f','image2pipe','-vcodec','png','pipe:1']
    try:
        raw=subprocess.check_output(cmd,stderr=subprocess.PIPE)
    except (OSError,subprocess.CalledProcessError) as e:
        raise RuntimeError('FFmpeg frame extraction failed') from e
    return Image.open(io.BytesIO(raw)).convert('RGB')

def main():
    p=argparse.ArgumentParser(description='Storyboard a reference video for VFX layer/timing analysis')
    p.add_argument('video');p.add_argument('--out',required=True)
    p.add_argument('--count',type=int,default=12)
    p.add_argument('--start',type=float,default=0)
    p.add_argument('--end',type=float)
    p.add_argument('--width',type=int,default=180)
    args=p.parse_args()
    meta=probe(args.video)
    total=float(meta['format']['duration'])
    end=total if args.end is None else min(args.end,total)
    if not 1<=args.count<=48 or end<=args.start or args.width<80:
        p.error('Invalid count, time range, or frame width')
    times=[args.start+(end-args.start)*i/args.count for i in range(args.count)]
    images=[frame(args.video,t,args.width) for t in times]
    cols=min(4,args.count);rows=math.ceil(len(images)/cols)
    h=max(im.height for im in images)
    margin=12;bottom=24
    sheet=Image.new('RGB',(cols*args.width+(cols+1)*margin,
                          rows*(h+bottom)+(rows+1)*margin),(26,29,34))
    d=ImageDraw.Draw(sheet)
    for i,(t,im) in enumerate(zip(times,images)):
        col,row=i%cols,i//cols
        x=margin+col*(args.width+margin);y=margin+row*(h+bottom+margin)
        sheet.paste(im,(x,y))
        d.text((x,y+h+3),f'{t:.2f} s',fill=(238,238,238))
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    sheet.save(out)
    print(f'Saved {len(images)} storyboard frames to {out} | source duration {total:.2f}s')

if __name__=='__main__':main()