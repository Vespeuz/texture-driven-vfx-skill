# Texture generation: procedural + image-model-assisted

The builder accepts both procedurally generated textures and externally generated textures.

## Atlas layout (RGBA, square, 4 x 4 cells)

| Cell row | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 1 | `beam` | `filament` | `ring` | `rune` |
| 2 | `spark` | `burst` | `glow` | `smoke` |
| 3 | `slash` | `flame` | `swirl` | `star` |
| 4 | unused | unused | unused | unused |

These 12 defaults are **not** a limitation on effect types. For a custom sprite set, define `"texture": {"tiles": ["portal", "shield", "electric_arc"]}` in the spec and provide the matching transparent PNGs with `--tiles`; the chosen names occupy cells left-to-right, then top-to-bottom. Up to 16 slots fit in the 4×4 grid. Any custom tiles without PNG files require an explicitly supplied full atlas.

Each icon is **one tile** and must have a transparent RGBA background. Keep edges clear to prevent neighboring atlas tiles from bleeding. The builder insets UV coordinates and clamps UV sampling.

### Procedural generation

Use without `--atlas` and `--tiles`. Palette is controlled by `texture.accent` and `texture.core` in JSON spec. A deterministic texture atlas is created by NumPy and Pillow.

### Image-generation-assisted workflow

If an image generation tool is available to the agent, generate **original** RGBA textures and save each as `name.png`, e.g. `beam.png`, `ring.png`. Place them in a directory, and run the builder with `--tiles path/to/tiles`. The builder fills missing texture types procedurally. No image-generation account or network integration is required by this package.

For a fully authored atlas, use `--atlas path/to/atlas.png`. The atlas must be square with identical 4 x 4 grid cells, arranged exactly as above. The builder does not automatically locate or segment multiple sprites from an arbitrary collage.

Prompt for a single `beam.png` tile:

> Original stylized real-time magic energy texture, vertical tapered beam occupying a single square RGBA canvas, intense pale central core and saturated blue edges, elegantly jagged turbulence, strong silhouette, soft anti-aliased transparency, zero background, no words, no perspective, no rendered 3D scene, game-ready flat emission mask, centered, generous transparent border.

Prompt for `ring.png`:

> Original thin magical shockwave ring texture, a circular broken glowing arc centered in a square RGBA canvas, bright inner edge, transparent background, no ground, no shadows, no perspective, no text, smooth alpha antialiasing, leave transparent padding on all edges.

Customize hue, line density, angularity, and distortion to match the effect. Never use a black opaque background masquerading as transparency. Check alpha with `validate_glb.py` and inspect it visually over dark and light backgrounds.

### Material constraint

This GLB generator packs only a single unlit RGBA color atlas. It does not animate color or emissive strength. Produce variations by generating distinct atlases and exports, or add verified runtime-specific shader/particle enhancements separately.
