"""Small dependency-free glTF/GLB inspection helpers for the VFX skill."""
from __future__ import annotations
import json
import struct
from pathlib import Path
from collections import Counter

MAGIC = b'glTF'
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942

def read_glb(path):
    data = Path(path).read_bytes()
    if len(data) < 20 or data[:4] != MAGIC:
        raise ValueError('Not a GLB file')
    magic, version, total = struct.unpack_from('<4sII', data)
    if version != 2 or total != len(data):
        raise ValueError(f'Invalid GLB header: version={version}, declared={total}, actual={len(data)}')
    off, root, binary = 12, None, b''
    while off < len(data):
        if off + 8 > len(data):
            raise ValueError('Incomplete GLB chunk header')
        size, ctype = struct.unpack_from('<II', data, off)
        off += 8
        if off + size > len(data):
            raise ValueError('GLB chunk exceeds end of file')
        chunk = data[off:off+size]
        if ctype == JSON_CHUNK:
            root = json.loads(chunk.decode('utf-8'))
        if ctype == BIN_CHUNK:
            binary = chunk
        off += size
    if root is None:
        raise ValueError('GLB has no JSON chunk')
    return root, binary

def triangles(root):
    accessors = root.get('accessors', [])
    total = 0
    for mesh in root.get('meshes', []):
        for prim in mesh.get('primitives', []):
            mode = prim.get('mode', 4)
            idx = prim.get('indices', prim.get('attributes', {}).get('POSITION'))
            count = accessors[idx]['count'] if idx is not None else 0
            if mode == 4:
                total += count // 3
            elif mode in (5, 6):
                total += max(count-2, 0)
    return total

def summarize(root, byte_count=None):
    animations = root.get('animations', [])
    channels = [ch for a in animations for ch in a.get('channels', [])]
    return {
        'bytes': byte_count,
        'triangles': triangles(root),
        'meshes': len(root.get('meshes', [])),
        'estimated_basepass_drawcalls': sum(len(root['meshes'][n['mesh']].get('primitives', [])) for n in root.get('nodes', []) if 'mesh' in n),
        'nodes': len(root.get('nodes', [])),
        'skins': len(root.get('skins', [])),
        'joints': sum(len(s.get('joints', [])) for s in root.get('skins', [])),
        'materials': len(root.get('materials', [])),
        'textures': len(root.get('textures', [])),
        'images': len(root.get('images', [])),
        'animations': len(animations),
        'animation_channels': len(channels),
        'animated_paths': dict(Counter(ch['target']['path'] for ch in channels)),
        'extensionsUsed': root.get('extensionsUsed', []),
        'alphaModes': dict(Counter(m.get('alphaMode', 'OPAQUE') for m in root.get('materials', [])))
    }

def encode_glb(root, blob):
    j = json.dumps(root, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    j += b' ' * ((4-len(j)%4)%4)
    b = blob + b'\0' * ((4-len(blob)%4)%4)
    length = 12 + 8 + len(j) + 8 + len(b)
    return (struct.pack('<4sII', MAGIC, 2, length) +
            struct.pack('<II', len(j), JSON_CHUNK) + j +
            struct.pack('<II', len(b), BIN_CHUNK) + b)