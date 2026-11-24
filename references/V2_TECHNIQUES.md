# v2.0 techniques and practical recipes

## Choose the right representation

| Need | Representation |
|---|---|
| Ring, rune, ground flare | Horizontal quad or ring mesh |
| Organic burst, smoke | Crossed RGBA cards or baked sequence |
| Tall circular beam | Open cylinder with wrap-friendly UV strip; separate impact cards |
| Twisting trail | Ribbon mesh with longitudinal UVs; native transforms/morphs |
| Exact source-camera motion | Authorized flipbook; not true volumetric reconstruction |

## Original or authorized sequences

```bash
# Original pre-rendered RGBA frames, named in ascending time order
python scripts/flipbook.py images frames --out packed --fps 30 --resolution 512 --columns 2 --rows 4
# Authorized footage only; background must match the cropped region
python scripts/flipbook.py video clip.mp4 --authorized --start 0.5 --duration 2.133333 --fps 30 --background clean_plate.png --out packed
# Bake original texture motion offline
python scripts/flipbook.py bake energy.png --kind distort --count 64 --fps 30 --out packed
```

`fps` is the intended sampling cadence, not an automatic detection of source frame rate. Inspect source cadence first (FFprobe); if variable frame rate, use timestamps or explicitly resample and disclose it. FFmpeg extraction may produce one fewer/more frame at interval edges; verify manifest counts. Matte estimation assumes a stationary matching clean plate. Moving backgrounds, additive glow and occlusion require manual compositing or original artwork. Keep crop and canvas consistent across frames. Padding must not shift the visual anchor. Do not feather across a texture's intended repeat seam: for wrap strips set `--edge 0` where appropriate and author seamless source artwork; the packer still places a transparent cell border.

## Full cadence, low geometry

```bash
python scripts/build_flipbook.py packed/manifest.json --shape cylinder --segments 8 --width 2 --height 48 --out raw.glb --report raw.json
python scripts/batch_drawcalls.py raw.glb --out batched.glb --max-draws 9 --max-joints 16
python scripts/check_flipbook.py batched.glb
```

64 frames, 8 frames per 512 atlas, 8-sided open cylinder: 1,024 triangles, eight expected base-pass primitives after rigid batching, 30 FPS. This is a single-layer demonstration, not a claim of a production-ready beam. Eight atlases at 512 RGBA consume 8 MiB uncompressed before mipmaps. More atlases/materials can be necessary to preserve cell resolution. A separate crossed impact sequence adds 256 triangles at 64 frames. Use synchronized layered packing below to share atlas materials and retain draw groups; retest transparency.

## Synchronized beam + impact + ground

Create a JSON plan (paths relative to the plan file):

```json
{
  "layers": [
    {"directory":"beam_frames","cell_rect":[0,0,0.5,1],"shape":"cylinder","width":2,"height":48,"segments":8,"anchor":0},
    {"directory":"impact_frames","cell_rect":[0.5,0,1,1],"shape":"cross","width":5,"height":3,"planes":2,"anchor":0,"offset":[0,-0.2,0]}
  ],
  "ground": {"image":"ring.png","width":7,"offset":[0,0.01,0]}
}
```

```bash
python scripts/flipbook.py layers plan.json --out packed_layers --fps 30 --resolution 512
python scripts/build_flipbook.py packed_layers/manifest.json --out effect_raw.glb
python scripts/batch_drawcalls.py effect_raw.glb --out effect.glb --max-draws 9 --max-joints 16
python scripts/check_flipbook.py effect.glb
```

All layer directories must have the same number of ordered frames. `cell_rect` is normalized `[left,top,right,bottom]` inside each frame cell. Choose layout and source aspect ratio deliberately; the packer fits rather than stretches source art. The per-layer `offset` is the mesh-local displacement (Y up); the example value is illustrative, not a universal alignment fix. A separately textured ground quad adds one draw group. The ground uses STEP onset/end, configurable via `on` and `off` in seconds; use baked ground animation in a layer for richer behavior. The 64-frame synthetic regression test yields 1,282 triangles and nine estimated base-pass draws. It does not certify visual quality or actual engine performance.

## Native mesh and morph animation

The static builder accepts optional layer properties `shape`, `segments`, `inner`, `turns`, `anchor` and `morph_bend`. Example layer excerpt:

```json
{"name":"curved_energy","texture":"beam","shape":"cylinder","width":2,"height":8,"segments":12,"anchor":0,"morph_bend":0.6,"frames":[{"t":0,"morph_weight":0,"scale":[0.01,0.01,0.01]},{"t":0.5,"morph_weight":1,"scale":[1,1,1]},{"t":1,"morph_weight":0,"scale":[0.01,0.01,0.01]}]}
```

The native morph example bends the mesh along height; it is not a general morph sculpting system. Use an explicitly subdivided ribbon or custom DCC geometry for richer deformations. The existing rigid batcher does not support morph targets. Retain separate compatible exports if needed.

## QA and performance

Match camera and timestamp before comparing rendered and reference PNGs. `compare_frames.py reference_frames rendered_frames --out compare.jpg` creates a sheet plus optional RGB difference metrics. Review alpha sorting and spatial alignment from several angles in the actual engine. Use `check_flipbook.py` to verify one visible frame at each sample midpoint and exact frame boundaries. A structurally valid GLB may still render incorrectly in an importer.

Reference for conceptual production principles: [VFX Apprentice — Textures, Meshes, and Shaders](https://www.vfxapprentice.com/blog/textures-meshes-shaders-vfx-basics). Custom shader effects remain optional runtime features; the portable output uses baked textures and native glTF animation.
