# Texture-Driven VFX Skill v2.0

[About this project](about.md) · [Agent skill instructions](SKILL.md)

A reusable, agent-independent VFX production skill that turns visual references into **lightweight, texture-driven, animated GLB** assets. Inspired by the technical construction of low-poly sprite effects, not by copying reference artwork.

The folder contains:

- `SKILL.md` — instructions for AI agents and artists
- `scripts/` — functional portable GLB analysis, original texture generation, animation construction and QA tools
- `examples/` — rising shockwave, healing pulse and slash arc specification files
- `output/` — generated example GLBs and procedural atlas (tested)
- `references/` — measured comparison and practical transparency/portability notes

## Install

For an AI coding agent that supports the Agent Skills `SKILL.md` convention, copy the **whole** `texture-driven-vfx-skill` directory into the agent's configured skills directory. Keep scripts and relative file paths together. The `SKILL.md` is plain text and portable; other agents can follow the exact same process by reading the file even if they do not automatically discover skills.

For manual or CI use, Python 3.10+ and these packages are sufficient:

```bash
python -m pip install -r requirements.txt
```

FFmpeg and FFprobe are optional, for storyboards and authorized video-derived flipbooks.

## Quick start

From the skill root:

```bash
# 1. Build a blue rising-shockwave demo with procedural atlas
python scripts/build_vfx.py --spec examples/rising_shockwave.json \
  --out output/rising_shockwave.glb --atlas-out output/rising_shockwave_atlas.png

# 2. Check the result. --strict treats budget warnings as failures.
python scripts/validate_glb.py output/rising_shockwave.glb --strict

# 3. Other example styles
python scripts/build_vfx.py --spec examples/healing_pulse.json --out output/healing_pulse.glb
python scripts/build_vfx.py --spec examples/slash_arc.json --out output/slash_arc.glb

# 4. Compare existing reference models
python scripts/analyze_glb.py "../megumin_explosion__vfx_test_1__oxterium.glb" "../vertical beam optimized FIX VISUAL.glb"

# 5. Optional reference-video storyboard (requires FFmpeg)
python scripts/inspect_video.py ../reference.mp4 --out output/storyboard.jpg --count 12
```

### Build with externally generated sprites

Save individually authored transparent images as `beam.png`, `ring.png`, `spark.png`, etc., then:

```bash
python scripts/build_vfx.py --spec examples/rising_shockwave.json \
  --tiles /path/to/generated_tiles \
  --out output/my_custom_shockwave.glb
```

You may also put `"tiles": ["shield", "lightning", "portal"]` inside the spec `texture` object and provide those uniquely named RGBA PNGs for entirely custom designs. Missing **built-in** tiles use original procedural textures; the user can provide all 12 if desired. Or supply one carefully aligned 4×4 RGBA atlas using `--atlas /path/to/atlas.png`.

## Draw-call optimization

The default generator uses independent TRS-animated meshes for the widest compatibility. Each visible mesh may require its own draw call, even if the effect uses only one texture and one material. For complex reference VFX, **prefer fewer than 10 base-pass draw submissions**, or fewer than 20 when needed for quality.

Use the bundled generic rigid-skin batcher to preserve all source geometry and animation while merging sprites by material (and chronological node order):

```bash
python scripts/batch_drawcalls.py output/rising_shockwave.glb \
  --out output/rising_shockwave_batched.glb --max-draws 9 \
  --max-joints 16 --report output/rising_shockwave_batched_report.json
```

The example becomes **one drawable mesh primitive** while retaining its original animation channels, textures, and 24 triangles. Batching adds rigid skin joints, a standard glTF 2.0 feature. **One drawable does not guarantee exactly one real draw call** in an engine with extra render passes. Skinning and transparent sorting must be tested in the final runtime; keep the original skin-free export as a fallback.

## Demo performance and structure

The included **rising shockwave** example has **24 triangles**, **7 meshes**, **1 material**, **1 embedded 512px texture**, **11 TRS animation channels**, **0 joints** and weighs about **135 KiB**. The packaged healing and slash examples are also playable GLB animation assets. These are *structurally validated*, not benchmarked/render-tested in your particular game engine.

## Grounding and limitations

- The provided reference video has multiple elemental rising pillar variants. This example is the blue/cyan interpretation.
- A GLB is not a Unity VFX Graph or GPU particle system; standard GLB node transforms cover scale/rotation/translation but not scrolling UV animation or animated opacity.
- `KHR_materials_unlit` is used with a standard PBR fallback and `alphaMode=BLEND`, but exact appearance depends on your renderer. Bloom is an engine-level postprocess, not contained in GLB.
- Low triangles do **not** guarantee low GPU cost. Crossed transparent planes can cause overdraw, particularly on mobile.
- User-provided GLB/video reference files are **not bundled**. The skill records their measurements in `references/REFERENCE_ANALYSIS.md`.

## Typical agent instruction

> Use the texture-driven-vfx skill to analyze this reference, decompose it into layers, generate original transparent textures, animate purpose-built low-poly meshes, output a portable self-contained GLB with a JSON spec and validate it. Select an appropriate geometry budget and preserve frame cadence; explain any runtime-specific visual differences.


## v2.0: full-rate flipbooks and custom geometry

The original static-sprite workflow is unchanged. New utilities support alpha extraction from a matching background plate, procedural baking, padded atlas packing, STEP-gated GLB flipbooks, low-poly meshes, native morphs, texture resizing and temporal validation. See [V2 techniques](references/V2_TECHNIQUES.md) and [SKILL.md](SKILL.md).

```bash
python scripts/flipbook.py images rgba_frames --out packed --fps 30
python scripts/build_flipbook.py packed/manifest.json --shape cylinder --segments 8 --height 48 --out effect.glb --batch
python scripts/check_flipbook.py effect.glb
python scripts/validate_glb.py effect.glb --max-tris 1500 --max-texture 512 --max-draws 9
```

Default new clip name: `Animation`. Never silently drop frames to meet a geometry target. The flipbook builder handles single sequences and synchronized layered atlases, including an optional ground circle. Independently timed sequences may still need DCC assembly. Rigid-skin playback, visual quality, and actual draw calls must be tested in the destination engine.
