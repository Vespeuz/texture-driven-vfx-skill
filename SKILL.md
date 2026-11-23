---
name: texture-driven-vfx
description: Analyze reference VFX images/videos/GLBs and produce minimal-geometry, texture-driven, self-contained animated glTF 2.0 GLB effects. Supports magic, attacks, healing, shockwaves, slashes, portals, explosions, and abstract effects using original RGBA atlases and TRS animation. Use when the user requests efficient portable VFX, low-poly animated GLB, transparent sprite-mesh VFX, or conversion of elaborate effects into a few texture-driven layers.
---

# Texture-Driven VFX — Universal Skill (v1.1)

## Purpose

Deliver visually compelling, light, portable **animated GLBs** through transparent 2D texture planes, a small amount of geometry, and node transform animation. Target glTF 2.0 viewers and engines rather than any one agent, DCC, or renderer.

**Source-of-truth priority:** user-supplied references and requirements > measured structure > artistic interpretation > defaults. Treat videos as visual reference, not as proof of source shader implementation.

## Required output for a finished VFX job

1. `<effect>.glb` with embedded texture(s), standard glTF TRS animation, correct scale and orientation.
2. `<effect>.json` editable effect specification and (if generated) `<effect>_atlas.png`.
3. Validation result including triangles, texture dimensions/count, node count, animation tracks, skins, materials, size, and portability warnings.
4. Include **estimated draw calls** (count rendered mesh primitives after batching) and note whether actual GPU draw calls were measured.
5. Short note on actual target-engine playback testing. **Never claim visually verified in the engine unless tested there.**

## Workflow

### 1. Analyze

- Inspect supplied GLBs with `python scripts/analyze_glb.py "model.glb" --json`. Record triangle counts, materials, atlas strategy, animations, skins and joints. If an attachment cannot be inspected, say so; don't invent statistics.
- For footage, use `python scripts/inspect_video.py clip.mp4 --out frames.png --start 0 --end 3 --count 12` (needs FFmpeg). Split the relevant moment into **startup, peak, sustain, fade/end**. Notice how the visual silhouette evolves.
- State which visual claims are observed and which are implementation hypotheses.
- Do not redistribute reference footage or third-party model textures unless the user has rights. Generate **original** texture shapes.

### 2. Decompose into visual layers

Identify at most 3–8 core layers initially. Prioritize, in order: silhouette, timing, color, motion, small details. Typical layers: impact ring, core glow, crossed beam quads, radial splash, energy filament, debris/sparks, residual fade. Reuse one alpha atlas where possible.

**Choose the simplest viable geometry**: 1 flat quad = 2 triangles; `planes: 2` = 4 triangles, `planes: 3` = 6 triangles. The crosses approximate visibility across camera angles. Do not use armatures or dense tube meshes unless the user explicitly requires them and simpler methods fail visual QA.

### 3. Plan budgets

Defaults for a normal spell: **<=200 triangles**, **1 RGBA atlas at 512×512**, **1 material**, **0 joints**, **<=2 MiB**. A hero VFX may use 1024 px or 200–500 triangles when justified. Treat these as starting *budgets*, not reasons to deliver inferior visuals. Track draw calls, transparency overdraw and texture memory—not polygons alone. **Prefer <10 draw submissions per complete effect, and accept <20 only when visual fidelity requires it.** Count actual renderable mesh primitives rather than materials, since many independently animated sprites can mean many draw calls with one material.

### 4. Author effect spec

Copy `examples/rising_shockwave.json`, `examples/healing_pulse.json`, or `examples/slash_arc.json`. Schema: `examples/vfx_spec.schema.json`. Choose an animation duration and add layers with these fields:

- `name`: unique name
- `texture`: any slot name from `texture.tiles` (defaults: `beam`, `filament`, `ring`, `rune`, `spark`, `burst`, `glow`, `smoke`, `slash`, `flame`, `swirl`, `star`)
- `orientation`: `vertical` or `horizontal`
- `width`, `height`: plane dimensions in meters or engine-relative scene units
- `planes`: 1–8 intersecting textured quads, 1 for ground effects, 2–3 for vertical hero effects
- `center`: static XYZ center, Y-up
- `frames`: ordered keys, `t` in seconds and optional `offset`, `scale`, `rotation_deg` XYZ arrays

**Animation constraints:** at least two keys per layer, strictly increasing and within duration. Only TRS transforms are supported. Keep last keys tiny or hand off stop/hide to the engine. Place the main pillar's initial center near the ground when scaling up so it does not expand equally through the ground.

### 5. Produce textures (both modes supported)

- **Procedural**: built-in deterministic RGBA atlas. Set `texture.accent`, `texture.core`, and `texture.resolution`.
- **AI-assisted**: if an image creation tool is available, generate **individual original transparent PNGs** and provide `--tiles path/to/folder`. If you have a correctly laid out 4×4 atlas, use `--atlas atlas.png`. No AI service is hardcoded in this skill.
- For entirely new effect types, set `texture.tiles` to 1–16 **custom slot names** and supply matching `--tiles name.png` files, or a prepacked `--atlas`. Do not force unusual effects into a beam/ring sprite.
- Keep silhouettes legible at normal gameplay resolution; do not rely solely on bloom. Check the alpha channel over dark and light backgrounds.
- Tile names/grid are fixed: read `references/TEXTURE_WORKFLOW.md`.

### 6. Export portable animated GLB

```bash
python -m pip install -r requirements.txt
python scripts/build_vfx.py --spec examples/rising_shockwave.json \
  --out output/rising_shockwave.glb \
  --atlas-out output/rising_shockwave_atlas.png \
  --report output/rising_shockwave_metrics.json
```

For AI-assisted texture sprites, append `--tiles /path/to/rgba-tiles`. This builder outputs self-contained `.glb`, 1 atlas, 1 `alphaMode=BLEND`, `doubleSided` unlit material, mesh quads, and a TRS animation. `KHR_materials_unlit` has a standard PBR fallback. No animation skeleton, morphs, runtime code, external image URLs, or engine-specific nodes.

### 7. Optimize draw calls (preferred <10, fallback <20)

Core glTF does **not** automatically batch independently animated nodes sharing one material. Count drawables, not just triangles or unique materials. Prefer under 10 mesh primitives/draw submissions in the base color pass. Batch by material + visual phase to retain approximate transparency ordering.

The optional core-glTF **rigid-skin batcher** converts one-joint rigid sprites into merged meshes without changing UVs, textures, triangles, or original TRS keyframes:

```bash
python scripts/batch_drawcalls.py output/rising_shockwave.glb \
  --out output/rising_shockwave_batched.glb --max-draws 9 --max-joints 16 \
  --report output/rising_shockwave_draws.json
```

This is a deliberate exception to the no-rig default: it adds **one rigid joint per sprite** (one vertex weight per vertex), while preserving the existing animation channels. GLB 2.0 skinning is part of the standard, not an engine-specific shader feature. Keep per-draw joint palettes small, typically <=16–32, to support common mobile/web pipelines. Export **both** a skin-free compatibility GLB and an optimized batched GLB when target-runtime skin playback is unknown.

**Do not claim measured draw calls merely because the GLB has nine primitives.** Estimate one base-pass submission per rendered primitive, then confirm with the target renderer's profiler. Shadow/depth/post-process passes can add draws; transparent sorting moves from individual sprites to larger batches and may change compositing. Check this visually. Some GLB previewers support node animation but not skinned animation.

### 8. Validate

```bash
python scripts/validate_glb.py output/rising_shockwave.glb \
  --max-tris 200 --max-texture 1024 --strict \
  --report output/rising_shockwave_validation.json
python -m unittest discover -s tests -v
```

Fail the job for malformed GLB, missing animation, invalid timing, broken alpha, or absent embedded texture. Budget excess should be reported; optimize and retest before accepting higher complexity. Open GLB in a glTF viewer or the actual runtime and inspect **start, peak, 3/4, and end frames**, all around 360° if relevant. Check alpha sorting, color, orientation, scale, and animation playback. Repeat after any changes.

### 9. Iterate *locally*

Change the smallest component responsible for visual defects. Do not rebuild working unrelated layers, replace external assets, or increase geometry without evidence. Offer multiple palette variants via new atlases and exports.

## Portability and honesty rules

- **Not universal in core glTF:** material alpha keyframe curves, scrolling UVs, additive blends, bloom, custom distortion, and camera-facing billboard constraints. These require target-runtime features/extensions; do not claim they exist in a plain GLB. This generator uses opacity baked into static textures plus transform-based onset/disappearance.
- Transparent geometry can look different in Blender, Three.js, Babylon, Unity and other viewers due to blending/sorting and tone mapping. Visual runtime test is mandatory before calling it production-ready.
- Never call a polygon count alone a performance benchmark; translucent overdraw and simultaneous effect count matter.
- No copyrighted reference images/textures are bundled; build original artwork inspired by the **technical** construction of the references, not a copied design.

## Companion files

- `README.md`: installation, quick starts and limitations
- `references/REFERENCE_ANALYSIS.md`: measured source comparisons
- `references/TEXTURE_WORKFLOW.md`: procedural / AI image workflows and atlas layout
- `examples/`: editable specifications and JSON Schema
- `scripts/`: analyze GLB, inspect video, generate textures, generate GLB, batch draws, validate GLB
- `output/`: tested sample animated GLBs and atlas