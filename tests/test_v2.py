import json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from flipbook import matte,pack,bake,pack_layers
from build_flipbook import build
from mesh_shapes import surface
from check_flipbook import check
from batch_drawcalls import batch,accessor
from optimize_textures import resize
from glb_utils import read_glb,summarize
from build_vfx import create
from atlas import make_atlas
from validate_glb import validate

class V2Tests(unittest.TestCase):
    def test_shapes(self):
        for shape,count in [('plane',2),('cross',4),('cylinder',16),('cone',16),('ring',16),('ribbon',16)]:
            with self.subTest(shape=shape):
                p,u,i=surface(shape,2,48,8)
                self.assertEqual(len(i)//3,count);self.assertLess(i.max(),len(p));self.assertTrue(np.all((u>=0)&(u<=1)))
        p,_,_=surface('cylinder',2,48,8);self.assertEqual(float(np.ptp(p[:,1])),48)
    def test_alpha_plate(self):
        bg=Image.new('RGB',(32,32),(20,30,40));im=bg.copy();ImageDraw.Draw(im).rectangle((8,8,23,23),fill=(200,220,250));a=matte(im,bg)
        self.assertEqual(a.getpixel((0,0))[3],0);self.assertGreater(a.getpixel((15,15))[3],200)
    def test_fullrate_batch_resize(self):
        with tempfile.TemporaryDirectory() as tmp:
            t=Path(tmp);im=Image.new('RGBA',(80,160));ImageDraw.Draw(im).ellipse((12,10,68,145),fill=(60,180,255,200));frames=bake(im,64,'distort');m=pack(frames,t,30,512,2,4)
            self.assertEqual(m['frame_count'],64);self.assertEqual(len(m['atlases']),8)
            for name in m['atlases']:
                a=np.asarray(Image.open(t/name));self.assertTrue(np.all(a[::128,:,3]==0));self.assertTrue(np.all(a[:,::256,3]==0))
            raw=t/'raw.glb';raw.write_bytes(build(t/'manifest.json','cylinder',2,48,8));self.assertTrue(check(raw)['pass'])
            dest=t/'batch.glb';report=batch(raw,dest,9,16);self.assertEqual(report['triangles'],1024);self.assertEqual(report['estimated_basepass_drawcalls'],8);self.assertTrue(check(dest)['pass']);self.assertTrue(validate(dest,max_tris=1500)['pass'])
            small=t/'small.glb';resize(dest,small,256);self.assertTrue(check(small)['pass']);self.assertEqual(summarize(read_glb(small)[0])['triangles'],1024)
            orig,ob=read_glb(dest);new,nb=read_glb(small)
            for a in orig['animations'][0]['samplers']:
                for k in ('input','output'):np.testing.assert_array_equal(accessor(orig,ob,a[k]),accessor(new,nb,a[k]))
    def test_layered_beam_and_ground(self):
        with tempfile.TemporaryDirectory() as tmp:
            t=Path(tmp);im=Image.new('RGBA',(32,64));ImageDraw.Draw(im).ellipse((4,8,28,56),fill=(40,190,255,220))
            for name in ('beam','impact'):
                (t/name).mkdir()
                for i in range(64):im.save(t/name/f'{i:03}.png')
            im.save(t/'ring.png');plan={'layers':[{'directory':'beam','cell_rect':[0,0,.5,1],'shape':'cylinder','width':2,'height':48,'segments':8},{'directory':'impact','cell_rect':[.5,0,1,1],'shape':'cross','width':5,'height':3,'planes':2,'offset':[0,-.2,0]}],'ground':{'image':'ring.png','width':7}}
            (t/'plan.json').write_text(json.dumps(plan));m=pack_layers(t/'plan.json',t/'atlas');self.assertEqual(len(m['atlases']),9)
            raw=t/'raw.glb';raw.write_bytes(build(t/'atlas/manifest.json'));dst=t/'batch.glb';r=batch(raw,dst,9,16)
            self.assertEqual(r['triangles'],1282);self.assertEqual(r['estimated_basepass_drawcalls'],9);self.assertTrue(check(dst)['pass'])
            self.assertTrue(validate(dst,max_tris=1500,max_texture=512)['pass'])
    def test_native_morph(self):
        spec={'duration_seconds':1,'texture':{},'layers':[{'name':'arc','texture':'beam','shape':'cylinder','segments':8,'morph_bend':.5,'frames':[{'t':0,'morph_weight':0},{'t':1,'morph_weight':1}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'m.glb';f.write_bytes(create(spec,make_atlas()));g,b=read_glb(f);self.assertEqual(g['animations'][0]['name'],'Animation');self.assertEqual(g['animations'][0]['channels'][0]['target']['path'],'weights');self.assertTrue(validate(f)['pass']);self.assertTrue(g['meshes'][0]['primitives'][0]['targets'])
    def test_baked_motion(self):
        im=Image.new('RGBA',(32,64));ImageDraw.Draw(im).rectangle((4,8,12,20),fill=(255,255,255,255))
        for kind in ['scroll','distort','erode']:
            a=bake(im,8,kind);self.assertEqual(len(a),8);self.assertTrue(any(x.tobytes()!=a[0].tobytes() for x in a[1:]))

if __name__=='__main__':unittest.main()
