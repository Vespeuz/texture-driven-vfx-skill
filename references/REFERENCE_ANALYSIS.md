# Observed references and design implications

These findings were measured directly from the three user-provided reference files. The original files are deliberately **not** included in this skill package (size and third-party asset rights). Users who have them can re-run `scripts/analyze_glb.py` against their own copies.

## A. Megumin Explosion — `megumin_explosion__vfx_test_1__oxterium.glb`

- 142 mesh triangles in 9 meshes / 9 primitives.
- 7 meshes consist of two triangles each (a quad); the remaining 2 consist of 64 triangles each.
- 22 glTF nodes; **zero skins/joints**.
- 1 animation with 24 channels: 9 scale, 9 rotation, 6 translation.
- 12 embedded images / 12 texture references, 6 materials, 5,379,268 bytes.
- Transparent `BLEND` materials; the source does **not** necessarily rely on one atlas.
- Images are mainly orange circular / geometric / swirl / burst motifs. Exact material behavior depends on target renderer.

**Transferable method:** render intricate visual shapes into texture alpha, animate cheap planes and simple solids using glTF transform tracks. Do not copy the original Megumin art, textures, or branded design. The demo skill uses original generated textures.

## B. Vertical beam — `vertical beam optimized FIX VISUAL.glb`

- 31,462 mesh triangles in 8 meshes / 8 primitives.
- 159 glTF nodes, 1 skin with 149 joints.
- 1 animation with 448 channels: 149 scale, 149 translation, 149 rotation, 1 morph-weight channel.
- 8 materials; 15 texture objects referencing 1 embedded image (2048px atlas based on inspection).
- 7,344,432 bytes, transparent materials and `KHR_materials_emissive_strength` extension.

**Avoid for lightweight effects:** skeletal motion across many bones, thousands of transparent polygons, unnecessary morphs and draw-layer duplication.

## C. Rising Shockwave — `Unity VFX - Stylized Rising Shockwave   #gamevfx.mp4`

- Video is 720 x 1280, 30 FPS, 1,208 frames (~40.27 s).
- Shows multiple colored variants of a rising luminous energy pillar.
- Repeating visible components include circular ground impact, rapid upward energy shape, narrower moving filaments, radial bursts/spikes, occasional sparks and dissipation.
- **Not proof of any specific Unity implementation:** mesh counts, shaders, exact particle systems, and material construction cannot be derived from video alone.

**Reduction plan:** central vertical textured quad stack + one ground ring + one glow + optional sparks and splash. Animate node transforms in glTF core, rather than reproducing undocumented proprietary shader graphs.

## Production budgets (targets, not universal laws)

- 0–200 triangles for a simple spell; 200–500 for a hero spell if visual assessment warrants it.
- 1 atlas (512px default, 1024px for hero details), 1 transparent material where possible.
- No skinning; generally 5–15 scene nodes and 5–30 animation channels.
- Aim for under 2 MiB per self-contained GLB. **Also measure alpha overdraw, pixel fill rate, and number of simultaneously active effects:** low polygon count alone does not guarantee mobile performance.

## Limitations / portability truth

- glTF 2.0 core animates node translation, rotation, and scale (plus morph weights). It does *not* provide universal material-opacity animation, scrolling UVs, true additive blending, or camera-facing billboards.
- This skill approximates fade through shrinking/glow textures; for real alpha keyframes or scrolling shaders, use a renderer-specific implementation and mark it as a separate engine-side enhancement.
- `KHR_materials_unlit` is used as an optional extension with PBR fallback; `alphaMode=BLEND` and `doubleSided=true` are standard. A render engine may sort cross-planes differently. Bloom is a postprocessing feature, not part of a GLB file.
- JSON and BIN structural checks are performed locally. Visual playback must still be inspected in the intended runtime before shipping.
