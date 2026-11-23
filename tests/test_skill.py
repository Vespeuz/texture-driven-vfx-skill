"""Offline regression tests; run from repo root with unittest discover."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from glb_utils import read_glb, summarize
from atlas import make_atlas
from build_vfx import create
from validate_glb import validate
from batch_drawcalls import batch

class SkillTests(unittest.TestCase):
    def test_all_examples_are_rig_free_and_animated(self):
        for f in sorted((ROOT/'examples').glob('*.json')):
            if f.name.endswith('.schema.json'):continue
            with self.subTest(f=f.name):
                spec=json.loads(f.read_text())
                tx=spec['texture']
                atlas=make_atlas(tx['resolution'],tx['accent'],tx['core'])
                data=create(spec,atlas)
                with tempfile.TemporaryDirectory() as tmp:
                    glb=Path(tmp)/'test.glb';glb.write_bytes(data)
                    root,_=read_glb(glb)
                    s=summarize(root,len(data))
                    self.assertLessEqual(s['triangles'],200)
                    self.assertEqual(s['skins'],0)
                    self.assertEqual(s['materials'],1)
                    self.assertEqual(s['textures'],1)
                    self.assertGreater(s['animation_channels'],0)
                    report=validate(glb,strict=True)
                    self.assertTrue(report['pass'],report)

    def test_drawcall_batcher_preserves_example_animation(self):
        spec=json.loads((ROOT/'examples/rising_shockwave.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'original.glb';dst=Path(tmp)/'batched.glb'
            src.write_bytes(create(spec,make_atlas()))
            metrics=batch(src,dst,max_draws=9,max_joints=16)
            original,_=read_glb(src)
            optimized,_=read_glb(dst)
            self.assertEqual(metrics['estimated_basepass_drawcalls'],1)
            self.assertEqual(metrics['triangles'],summarize(original)['triangles'])
            self.assertEqual(metrics['animation_channels'],summarize(original)['animation_channels'])
            self.assertEqual(len(optimized['skins']),1)
            self.assertTrue(validate(dst)['pass'])

    def test_invalid_animation_is_rejected(self):
        spec=json.loads((ROOT/'examples/slash_arc.json').read_text())
        spec['layers'][0]['frames'][1]['t']=0
        with self.assertRaises(ValueError):
            create(spec,make_atlas())

    def test_rgba_atlas_is_not_opaque(self):
        atlas=make_atlas(512)
        self.assertEqual(atlas.mode,'RGBA')
        self.assertEqual(atlas.getchannel('A').getextrema()[0],0)
        self.assertGreater(atlas.getchannel('A').getextrema()[1],0)

if __name__=='__main__':unittest.main()
