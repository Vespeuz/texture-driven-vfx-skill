# About Texture-Driven VFX

**Texture-Driven VFX v2.0** is an open, agent-independent workflow for building lightweight, animated 3D visual effects from reference images, videos, and existing GLB assets.

Its goal is to **make an effect visually rich without making its geometry unnecessarily complex**. Rather than sculpting every flame, shockwave, or energy filament from polygons, the workflow uses original transparent RGBA artwork on simple, purpose-built meshes, animated using features available in glTF 2.0.

## What it helps create

Rising shockwaves, magic spells, explosions, healing pulses, sword slashes, portals, and other stylized effects. The repository provides example specifications for a **rising shockwave**, **healing pulse**, and **slash arc**.

## How it works

1. **Analyze the reference.** Break the effect into startup, peak, sustain, and fade, and identify its most important shapes and movements.
2. **Design texture layers.** Create original alpha sprites procedurally or supply AI-assisted / artist-made transparent PNGs. Pack them into an atlas.
3. **Build minimal geometry.** Place sprites on purpose-built planes, crossed cards, cylinders, rings, cones, or ribbons. Add complexity only when it improves the result.
4. **Animate for portable GLB.** Export embedded textures, standard materials, and node translation/rotation/scale (TRS), native morph animation, and STEP-gated baked flipbooks.
5. **Validate and optimize.** Check triangles, materials, embedded images, animation channels, file size, and estimated draw submissions. Optionally batch compatible animated sprites using standard glTF skinning.

## Design principles

- **Visual fidelity comes first.** Low triangle counts are a constraint, not proof of artistic quality.
- **Textures do most of the visual work.** Invest in silhouettes, alpha edges, gradients, color, and carefully composed layers.
- **Use geometry deliberately.** Simple planes are effective, but not every shot or camera angle can be solved with a single billboard.
- **Measure performance honestly.** Aim for fewer than **10 base-pass draw submissions** where practical, with fewer than **20** as a fallback. Actual renderer draw calls and transparent overdraw must be profiled in the destination engine.
- **Keep outputs inspectable.** Preserve editable JSON specs, source images, and QA reports alongside GLBs.
- **Keep source assets original.** Reference footage and third-party models are not included or redistributed.

## What is included

- `SKILL.md` — portable agent workflow and build instructions
- `scripts/` — video inspection, GLB inspection, atlas generation, animated GLB building, draw-call batching, and validation
- `examples/` — effect specifications and a JSON Schema
- `output/` — small demonstration GLBs, an atlas, and validation reports
- `references/` — measured reference comparisons and texture-workflow guidance
- `tests/` — regression tests for the included pipeline

## Compatibility and limitations

The output is designed around **glTF 2.0 / GLB** portability, not a specific game engine. A standard GLB can carry textures, meshes, materials, node TRS animation, and skin animation, but it **does not automatically carry custom Unity, Unreal, Blender, or WebGL shaders**. UV scrolling, shader distortion, animated flipbook sampling, bloom, and game-specific particle behavior need runtime support or a baked approximation.

Texture-driven recreation is **not an automatic 1:1 converter**: a single-camera video cannot reveal the original effect's full geometry, shaders, or occluded motion. QA should compare rendered output against the reference at multiple timestamps and angles, and test it in the actual destination runtime.

## Getting started

See [README.md](README.md) for setup and commands, or [SKILL.md](SKILL.md) for the complete agent workflow.

**Guiding idea: make it look expensive, but render cheaply.**

## What changed in v2.0

Full-cadence flipbooks, optional authorized video alpha extraction, baked texture motion, custom low-poly UV meshes, native morph animation, texture resizing and temporal validation. Preserve visual fidelity before optimizing; do not reduce animation cadence to meet a triangle budget. See [V2 techniques](references/V2_TECHNIQUES.md).
