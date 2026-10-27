from pathlib import Path
import sys,json,struct,tempfile,unittest,contextlib,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from window import SHELF,TOP,TAPER,BEVEL,apply_window
from build import cut_depth,build
from nif_mesh import identity,assemble
from nif_io import blocks,read_sse

@contextlib.contextmanager
def fixture_dir():
 base=ROOT/'build/test-temp';base.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=base) as folder:
  assert Path(folder).resolve().parent==base.resolve()
  yield folder

class SourceChecks(unittest.TestCase):
 def test_release_window_profile(self):
  self.assertAlmostEqual(SHELF,3.9707460691833494)
  self.assertAlmostEqual(TOP,17.595611910377503)
  self.assertAlmostEqual(TAPER,12.495611910377502)
  self.assertAlmostEqual(BEVEL,.2125)
 def test_release_cut_depth(self):
  points=[[0,8,-2],[0,8,2]]
  for hand in ('left','right'):
   depth=cut_depth(points,hand,'weapons/example/bow.nif')
   self.assertAlmostEqual(depth,.6181818181818182)
   self.assertGreater(depth,0);self.assertLess(depth,1)
 def test_fomod_has_one_choice_and_both_routes(self):
  root=ET.parse(ROOT/'fomod/ModuleConfig.xml').getroot();group=root.find('.//group');self.assertEqual(group.attrib['type'],'SelectExactlyOne')
  choices=group.findall('./plugins/plugin');self.assertEqual(len(choices),2)
  self.assertEqual({p.find('./files/folder').attrib['source'] for p in choices},{'left\\meshes','right\\meshes'})
  self.assertTrue(all(p.find('./files/folder').attrib['destination']=='meshes' for p in choices))
 def test_reference_has_safe_complete_unique_paths(self):
  rows=json.loads((ROOT/'reference_sources.json').read_text())['meshes'];self.assertEqual(len(rows),34);self.assertEqual(len({r['path'] for r in rows}),34)
  for row in rows:
   p=Path(row['path']);self.assertFalse(p.is_absolute());self.assertNotIn('..',p.parts);self.assertEqual(p.suffix,'.nif');self.assertEqual(len(row['sha256']),64)
   self.assertEqual(set(row['referenceOutputs']),{'left','right'});self.assertNotEqual(row['referenceOutputs']['left'],row['referenceOutputs']['right'])
 def test_missing_input_does_not_create_output(self):
  with fixture_dir() as t:
   source=Path(t)/'source';source.mkdir();out=Path(t)/'out'
   with self.assertRaises(FileNotFoundError):build(source,out)
   self.assertFalse(out.exists())
 def test_wrong_source_hash_is_rejected(self):
  with fixture_dir() as t:
   source=Path(t)/'source';out=Path(t)/'out';first=json.loads((ROOT/'reference_sources.json').read_text())['meshes'][0];p=source/first['path'];p.parent.mkdir(parents=True);p.write_bytes(b'synthetic wrong input')
   with self.assertRaisesRegex(ValueError,'does not match'):build(source,out)
   self.assertFalse(out.exists())
 def test_nested_source_output_is_refused(self):
  with fixture_dir() as t:
   with self.assertRaisesRegex(ValueError,'non-nested'):build(Path(t),Path(t)/'out')
 def test_opaque_block_preservation(self):
  kind=b'SyntheticOpaque';header=b'Gamebryo File Format, Version 20.2.0.7\n'+struct.pack('<IBIII',0x14020007,1,12,2,100)+b'\0\0\0'+struct.pack('<HI',1,len(kind))+kind+struct.pack('<2H2I3I',0,0,2,4,0,0,0)
  data=header+b'abkeep'+struct.pack('<I',0);self.assertEqual(read_sse(data)['stream'],100)
  changed=assemble(data,{0:b'new'});parsed=blocks(changed);self.assertEqual(parsed[0][2],b'new');self.assertEqual(parsed[1][2],b'keep')

class FakePart:
 def __init__(self):
  points=[[0,0,-1.5],[0,0,1.5],[0,24,1.5],[0,24,-1.5],[-13,-2,-.05],[-13,25,-.05],[-13,25,.05]]
  self.vertices=[dict(p=p[:],uv=[0,0],n=[-1,0,0],t=[0,1,0],bit=[0,0,1],color=[],w={0:1.}) for p in points]
  self.root_positions=[p[:] for p in points];self.raw=[bytearray(40) for p in points];self.original_count=len(points);self.triangles=[(0,1,2),(0,2,3),(4,5,6)];self.original_triangles=self.triangles[:]
 def write_vertex(self,i,p,n,t,bit):self.raw[i]=b'generated'
class GeometryChecks(unittest.TestCase):
 def test_shelf_and_string_island_are_preserved(self):
  p=FakePart();original=[v['p'][:] for v in p.vertices];result=apply_window(dict(part=p,mapping=identity()),'left',.7)
  self.assertEqual(result['protectedStringVertices'],3)
  for i in range(len(original)):self.assertEqual(p.preview_after[i],original[i])
  self.assertTrue(any(abs(q[1]-SHELF)<1e-8 for q in p.preview_before[7:]))
  self.assertTrue(any(abs(q[1]-TOP)<1e-8 for q in p.preview_before[7:]))
  self.assertTrue(any(a!=b for a,b in zip(p.preview_before,p.preview_after)))
 def test_handed_operations_are_mirrored(self):
  outputs=[]
  for hand in ('left','right'):
   p=FakePart()
   if hand=='right':
    for v,q in zip(p.vertices,p.root_positions):v['p'][2]=-v['p'][2];q[2]=-q[2]
   apply_window(dict(part=p,mapping=identity()),hand,.7)
   outputs.append(sorted(tuple(round(x,6) for x in (q[0],q[1],q[2] if hand=='left' else -q[2])) for q in p.preview_after if q[0]>-9))
  self.assertEqual(outputs[0],outputs[1])
if __name__=='__main__':unittest.main()
