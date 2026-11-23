#!/usr/bin/env python3
"""Inspect a reference GLB without Blender."""
import argparse, json
from pathlib import Path
from glb_utils import read_glb, summarize

def main():
    p = argparse.ArgumentParser(description='Inspect mesh, texture, rig and animation complexity in GLB files')
    p.add_argument('glbs', nargs='+')
    p.add_argument('--json', action='store_true')
    args = p.parse_args()
    results = {}
    for name in args.glbs:
        path = Path(name)
        root, _ = read_glb(path)
        results[path.name] = summarize(root, path.stat().st_size)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for name, metrics in results.items():
            print(f'\n{name}')
            for key, value in metrics.items():
                print(f'  {key}: {value}')

if __name__ == '__main__':
    main()