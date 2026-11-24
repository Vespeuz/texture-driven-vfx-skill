# Texture-Driven VFX Skill

Create visually rich, lightweight **animated GLB effects** from reference videos, images, original textures, or existing 3D assets. A portable Agent Skill for AI coding agents, technical artists, and real-time game developers.

**Input:** A VFX reference or effect brief. **Output:** A self-contained animated glTF 2.0 asset, texture atlases, editable specifications, and validation reports.

[Install the skill](#installation) · [Quick start](#quick-start) · [Example prompts](#example-prompts) · [SKILL.md](SKILL.md) · [About](about.md)

## What this skill solves

Complex real-time effects often require large geometry budgets, expensive transparent layers, or renderer-specific shaders. This skill combines detailed RGBA textures, carefully shaped low-poly meshes, and native glTF animation to produce portable visual effects with measurable performance budgets.

**Make it look expensive, but render cheaply.**

## Why this is a skill (model delta)

The skill encodes three types of practical value: retro-born failure patterns, executable scripts and validators, and anti-rationalization guards. Without a dedicated workflow, an agent may reduce flipbook frame count to meet a geometry budget, producing choppy motion while reporting a successful optimization.

The [regression tests](tests/test_v2.py) verify frame cadence, texture processing, layered geometry and draw-group budgets; [legacy tests](tests/test_skill.py) cover the original pipeline. These are deterministic implementation checks; no controlled model-with/without-skill A/B evaluation is published.

## Use when

- Reconstruct a magic spell, explosion, shockwave, slash, healing effect, portal, or other stylized VFX.
- Build a portable animated GLB from original RGBA textures or authorized reference footage.
- Create a beam, ribbon, ring, cylinder, cone, or crossed-plane effect with minimal geometry.
- Preserve fluid animation while reducing triangles, draw submissions, or texture memory.
- Inspect and optimize an existing GLB for a real-time 3D or web-based project.

## Expected outputs

| Output | Description |
| --- | --- |
| Animated GLB | Embedded textures, standard glTF materials, native animation; default clip name `Animation` |
| RGBA textures | Original sprites, padded atlases, or authorized baked sequences |
| Editable inputs | JSON effect specifications or flipbook manifests |
| QA report | Triangle count, texture dimensions, animation timing, estimated draw submissions, and portability notes |
| Visual review | Reference comparison sheets and target-engine playback checks where available |

## Context requirements

Provide a video, image, GLB, or written effect brief. For accurate recreation, specify the relevant video interval, viewing angles, timing, palette, target runtime, and performance constraints. Supply a matching clean background plate when extracting transparency from footage. Use only reference artwork that you have permission to process and redistribute.

The default atlas budget is 512 × 512 per texture. Preserve source cadence, use visual quality to guide geometry decisions, and aim for fewer than 10 base-pass draw submissions (fewer than 20 when justified).

## Example prompts

- "Use the texture-driven-vfx skill to create a cyan rising shockwave from this video. Ignore the avatar, match the visual timing, and export an animated GLB."
- "Build a cylindrical magic beam with a separate impact layer and my supplied magic circle. Preserve 30 FPS texture motion, target 1,000–1,500 triangles and fewer than 10 draw submissions."
- "Create a stylized healing spell with original transparent textures, a rotating ground rune, and floating sparks. Export with 512 × 512 atlases and the animation named Animation."
- "Inspect this GLB and reduce its texture memory and unnecessary geometry without dropping animation frames. Report the trade-offs and validation results."

## Related skills

None maintained as a formal companion in this repository. The skill can work with independent image-generation and 3D authoring tools. See [the technique guide](references/V2_TECHNIQUES.md) for production references.

## Installation

Clone the repository:

```bash
git clone https://github.com/Vespeuz/texture-driven-vfx-skill.git
cd texture-driven-vfx-skill
python -m pip install -r requirements.txt
```

Python 3.10+ is required for the bundled scripts. Install FFmpeg and FFprobe for optional video inspection and authorized video-derived flipbook processing.

For an agent that supports Agent Skills, copy the complete repository folder into its configured skills directory, keeping `SKILL.md`, scripts, examples, and references together. Other agents can read [SKILL.md](SKILL.md) directly. The skill is distributed through this repository and uses manual installation rather than a registered marketplace.

## Showcase

<p align="center">
  <img src="assets/magic-spell-vfx.png" alt="Blue cylindrical magic beam with a cyan magic circle, shown in the Blender viewport" width="707">
</p>

*Blue cylindrical magic beam with a custom magic circle — Blender viewport preview of the animated GLB.*

### Example geometry budgets

| Example | Triangles | Expected base-pass submissions | Animation |
| --- | ---: | ---: | --- |
| Procedural rising shockwave | 24 | 7 before optional batching | TRS |
| Full-rate cylindrical flipbook (synthetic regression) | 1,024 | 8 after batching | 64 frames at 30 FPS |
| Cylinder + impact + ground (synthetic regression) | 1,282 | 9 after batching | 64 frames at 30 FPS |

These figures describe structural regression configurations, not measured GPU performance or a guarantee of visual quality. Profile actual draw calls and inspect animation in the destination renderer.

## Quick start

Build an original procedural effect:

```bash
python scripts/build_vfx.py --spec examples/rising_shockwave.json \
  --out output/rising_shockwave.glb --atlas-out output/rising_shockwave_atlas.png

python scripts/validate_glb.py output/rising_shockwave.glb --strict

python scripts/build_vfx.py --spec examples/healing_pulse.json --out output/healing_pulse.glb
python scripts/build_vfx.py --spec examples/slash_arc.json --out output/slash_arc.glb
```

Use custom transparent sprites with the same specification:

```bash
python scripts/build_vfx.py --spec examples/rising_shockwave.json \
  --tiles /path/to/generated_tiles --out output/my_custom_shockwave.glb
```

For custom designs, list unique slot names in `texture.tiles` and supply matching RGBA PNG files. A correctly aligned 4×4 atlas can also be supplied with `--atlas`.

### Full-rate texture animation

```bash
python scripts/flipbook.py images rgba_frames --out packed --fps 30 --resolution 512
python scripts/build_flipbook.py packed/manifest.json --shape cylinder --segments 8 --height 48 --out effect.glb --batch
python scripts/check_flipbook.py effect.glb
python scripts/validate_glb.py effect.glb --max-tris 1500 --max-texture 512 --max-draws 9
```

See [V2 techniques and recipes](references/V2_TECHNIQUES.md) for authorized video extraction, offline shader-effect baking, synchronized beam and impact layers, and morph animation.

### Optimize existing effects

```bash
python scripts/analyze_glb.py output/rising_shockwave.glb
python scripts/batch_drawcalls.py output/rising_shockwave.glb \
  --out output/rising_shockwave_batched.glb --max-draws 9 \
  --max-joints 16 --report output/rising_shockwave_batched_report.json
```

The optional rigid-skin batcher preserves geometry and transform keyframes while merging compatible sprites. Keep a skin-free compatibility export when the target viewer has unknown skinning support. Morph-target effects require a compatible separate workflow.

## Techniques and tools

| Technique | Tool or guide |
| --- | --- |
| Original RGBA sprites and static effects | [atlas.py](scripts/atlas.py), [build_vfx.py](scripts/build_vfx.py) |
| Flipbooks, alpha extraction, baked motion | [flipbook.py](scripts/flipbook.py) |
| Shader-independent flipbook export | [build_flipbook.py](scripts/build_flipbook.py) |
| Custom meshes and UVs | [mesh_shapes.py](scripts/mesh_shapes.py) |
| Native transforms and morphs | [build_vfx.py](scripts/build_vfx.py) |
| Rigid-skin draw batching | [batch_drawcalls.py](scripts/batch_drawcalls.py) |
| Texture resizing | [optimize_textures.py](scripts/optimize_textures.py) |
| Video inspection | [inspect_video.py](scripts/inspect_video.py) |
| Structural, temporal and reference QA | [validate_glb.py](scripts/validate_glb.py), [check_flipbook.py](scripts/check_flipbook.py), [compare_frames.py](scripts/compare_frames.py) |

## Compatibility and limitations

Portable GLBs use embedded textures, standard materials and native glTF animation. UV scrolling, shader distortion, material animation, camera-facing billboards, and bloom require runtime support or an offline approximation. Unlit materials use `KHR_materials_unlit` with a standard PBR fallback.

Video-derived flipbooks preserve a reference camera's appearance; a single viewpoint cannot establish exact volumetric geometry. Visual fidelity, transparency sorting, skinning and actual draw calls need verification in the destination engine. Low triangle counts alone do not establish GPU performance: texture memory and transparent overdraw also matter.

Original or authorized reference assets are supplied locally. Generated GLBs and atlases can be reproduced using the scripts; see [output instructions](output/README.md).

## Contributing

Open an [issue](https://github.com/Vespeuz/texture-driven-vfx-skill/issues) or submit a pull request with a reproducible example. Preserve existing workflows, add regression coverage for new behavior, and report actual visual and structural test results separately. Avoid committing private or unauthorized reference footage.

Run the automated tests from the repository root:

```bash
python -m unittest discover -s tests -v
```

## License

Released under [The Unlicense](LICENSE). Free for everyone to use, modify, share, and sell, for personal or commercial purposes. No attribution required. Provided as-is, without warranty.

Third-party materials, if any, remain subject to their respective rights.
