---
name: texture-driven-vfx
description: Create or revise visually rich, lightweight animated GLB effects from authorized video, image, or GLB references. Use original RGBA textures, flipbooks, custom low-poly UV meshes, native glTF animation, and measured optimization. Supports magic, fire, explosions, beams, healing, slashes, portals and abstract effects.
---

# Texture-Driven VFX — Universal Skill v2.0

**Make it look expensive, but render cheaply.** Prioritize visual fidelity and motion; optimize spatial complexity before temporal fidelity. A low triangle count is not evidence of artistic quality.

## 1. Core VFX techniques

- **Layer decomposition:** inspect the reference at source cadence and identify the startup, peak, sustain and fade. Separate silhouettes and motion into independently controlled core, shell, impact, ring, sparks or other relevant layers. Record observed timing, not invented implementation details. Ignore unrelated subjects. Use the provided reference as the source of truth.
- **RGBA texture generation:** design original transparent sprites and strips with readable silhouettes, internal color/energy detail, rich alpha gradients and deliberate edges. Use procedural generation (`scripts/atlas.py`) or supply AI/artist-authored RGBA PNGs to `build_vfx.py --tiles`. For cylinders, use a wrap-friendly energy texture; avoid wrapping an entire perspective impact image around a tube.
- **Flipbook animation and atlas packing:** retain the original animation cadence and every meaningful frame. Pack fixed-size, padded cells with explicit UV rectangles and time metadata. Choose grid and atlas count according to texel density, file size and draw budget, not a fixed frame cap. `scripts/flipbook.py` packs sequences and emits a manifest.
- **Low-poly geometry and UVs:** choose planes, crossed planes, open cylinders, cones, rings or ribbons based on the reference silhouette and view angles. `scripts/mesh_shapes.py` provides normalized UVs and geometry; `build_vfx.py` accepts `shape`, `segments`, `anchor`, `inner` and `turns` per layer. Use no subdivisions that do not alter silhouette or deformation. Beam length does not require extra triangles. `anchor=0` means a vertical shape grows from its base; `.5` centers it.
- **Crossed planes:** use for broad sprites that need limited side-view presence, but not when a cylindrical silhouette is required. They are an approximation, not true volume.
- **Native transforms:** animate translation, rotation and scale with glTF TRS tracks. Use continuous interpolation for motion and STEP for discrete frame switching. Preserve the timing, origin and other working layers on revisions.

## 2. Advanced VFX techniques

| Technique | Workflow / implementation |
|---|---|
| Authorized video-derived flipbooks | `flipbook.py video`: extract at chosen source cadence, crop with consistent bounds, use a matching clean background plate. Only with permission to extract artwork; do not bundle third-party media. |
| Alpha reconstruction | `flipbook.py` estimates straight RGBA from a clean plate. Additive glow/unknown backgrounds are ambiguous; inspect dark and light composites and manually refine where needed. |
| Shader-independent flipbook playback | `build_flipbook.py`: fixed UV meshes with STEP scale gating, one visible frame at a time. Optional rigid batching. All frames remain represented in geometry, so budget scales with frame count. No native texture-index switching assumed. |
| Morph animation | `build_vfx.py`: optional `morph_bend` and per-key `morph_weight` (0–1) produce a native glTF POSITION morph target. For richer deformation author custom morph targets in a DCC. |
| Layered volumetric approximation | Combine nested textured shells, ribbons and crossed cards for depth. Choose layer order deliberately; transparent sorting is engine-dependent. |
| Baked shader effects | `flipbook.py bake --kind scroll/distort/erode` generates simple offline texture motion. Author richer sequences externally when needed. No custom runtime shader is embedded. |
| Rigid-skin batching | `batch_drawcalls.py` merges compatible TRS-animated, indexed single-primitive sprites with one rigid joint per sprite. Preserves source geometry and animation. Does not accept existing skins, morphs or nested hierarchies. |

For effects with a distinct impact and tall column, keep them as separate layers and textures. Do not stretch the impact artwork along the full beam. For synchronized layers, use `flipbook.py layers` with a JSON plan of per-layer frame directories, subrects and geometry settings. The shared atlas and merged per-frame primitive retain one STEP gate per timestamp. Include transparent frames for inactive phases, and optionally a separate ground texture. Arbitrarily timed independent layers may still need DCC assembly.

## 3. Optimization strategies

- **Temporal fidelity:** never silently drop, deduplicate or retime frames to meet triangle or draw budgets. Preserve source cadence (e.g. 64 frames at 30 FPS). Use `check_flipbook.py` before and after batching and texture resizing. Time metadata alone is insufficient: check actual STEP tracks. Ask before trading motion quality for size.
- **Geometry:** remove unused shells and subdivisions, reduce radial segments only if the silhouette remains acceptable, and use separate simplified cards for the impact. A simple effect may target 200 triangles; animated hero effects can justify 1,000–1,500 or another user-specified budget. Budget math: N frames × triangles per frame + other layers. An eight-sided open cylinder has 16 triangles; 64 such frames = 1,024 triangles. Two impact cards per frame add 256; a ground quad adds 2, giving 1,282 total. The layered regression test builds and checks this exact structural configuration using original synthetic sprites.
- **Draw calls:** prefer <10 base-pass submissions; <20 fallback. Estimate by drawable primitives, not material count. Batch by atlas/material and joint palette; report actual renderer measurements separately. Keep skin-free compatibility output when importer behavior is unknown.
- **Textures:** default 512×512 atlas; balance cell resolution, count, alpha padding and file size. `optimize_textures.py` resizes embedded PNG/JPEG views and retains geometry and animation data. Prefer aspect-preserving resize, avoid unnecessary upscaling, and inspect UV cell bleed afterward. KTX2/Basis is optional only if runtime supports it (not implemented here).
- **Overdraw:** minimize overlapping translucent shells and unnecessary invisible geometry. Hidden/degenerate flipbook frames can still incur vertex processing. Draw-count and triangle metrics do not measure fill cost. Profile target renderer with simultaneous casts.

## 4. Quality control

1. Compare reference and rendered start, peak, sustain and end frames at matching time and camera; use `compare_frames.py` to make a side-by-side sheet. Review actual playback at normal speed and multiple viewing angles. No automatic metric substitutes for artistic review.
2. Inspect RGBA over dark and light backgrounds; leave enough transparent image area to contain the full energy shape, feather only outer edges, and pad atlas cells. Avoid hard rectangular borders, background ghosts and clipping. If the source itself cuts off the effect, reconstruct the missing extent or disclose the limitation.
3. Check visible-pixel contact between impact, beam and ground circle throughout the animation; transparent padding can create a floating visual even when geometry touches the floor. Correct only affected layer offsets. Check texture aspect ratio, scale and orientation.
4. Run `validate_glb.py` with the agreed budgets; inspect embedded images, mesh/animation tracks and playback. Check the full-rate flipbook using `check_flipbook.py`. Existing validator may warn about multiple textures/materials, skins and morphs: these are review points, not proof of invalid glTF. Do not ignore structural errors.
5. Test transparency, unlit rendering, skin/morph support and actual draw calls in the destination engine. Report what was tested and what remains unverified. Do not label a single-camera reconstruction 1:1 in 3D.

## 5. Export conventions

- Default clip name `Animation`; preserve explicitly requested clip names. Self-contained glTF 2.0 GLB, Y-up, embedded RGBA textures (512×512 default for square atlases), standard materials and native animation. `KHR_materials_unlit` is optional with PBR fallback. No mandatory custom shader, runtime code, external image URL or engine-specific extension.
- Deliver GLB, editable effect JSON/flipbook manifest, source sprites or atlases where licensed, validation metrics, temporal report for flipbooks, and preview/comparison when available. Retain original files; make revisions locally.
- Runtime-specific additive blend, animated UV/material sampling, bloom, particle simulation and billboarding are not core GLB behaviors. Bake or approximate rather than claim portability.

## Commands (from skill root)

```bash
python -m pip install -r requirements.txt
python scripts/inspect_video.py reference.mp4 --out storyboard.jpg --count 12
python scripts/build_vfx.py --spec examples/rising_shockwave.json --out effect.glb
python scripts/flipbook.py images rgba_frames --out packed --fps 30 --resolution 512
python scripts/build_flipbook.py packed/manifest.json --shape cylinder --segments 8 --width 2 --height 48 --out raw.glb
python scripts/batch_drawcalls.py raw.glb --out batched.glb --max-draws 9 --max-joints 16
python scripts/check_flipbook.py batched.glb
python scripts/validate_glb.py batched.glb --max-tris 1500 --max-texture 512 --max-draws 9
python scripts/optimize_textures.py batched.glb --out resized.glb --resolution 512
python -m unittest discover -s tests -v
```

See `references/V2_TECHNIQUES.md` for practical recipes and limitations. The v1 static sprite workflow remains supported.
