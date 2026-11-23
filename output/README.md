# Generated VFX demonstrations

Run the commands in the repository root to regenerate the demonstration GLBs and their source texture atlas:

```bash
python scripts/build_vfx.py --spec examples/rising_shockwave.json --out output/rising_shockwave.glb --atlas-out output/rising_shockwave_atlas.png
python scripts/build_vfx.py --spec examples/healing_pulse.json --out output/healing_pulse.glb
python scripts/build_vfx.py --spec examples/slash_arc.json --out output/slash_arc.glb
python scripts/batch_drawcalls.py output/rising_shockwave.glb --out output/rising_shockwave_batched.glb --max-draws 9 --max-joints 16
```

The demonstration binaries are generated artifacts; the source specifications and reproducible Python generator are versioned in this repository. Visual testing in the destination renderer remains necessary.
