"""Build the reference FOMOD locally from the user's own source meshes."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
from nif_mesh import Mesh
from window import apply_window,SHELF,TOP

ROOT=Path(__file__).resolve().parents[1]
def cut_depth(points,hand,path):
 sign=1 if hand=='left' else -1
 side=[sign*q[2] for q in points if q[0]>=-6 and 4.22<=q[1]<=14]
 maximum=max(side,default=1.5);minimum=min(side,default=-1.5)
 base_depth=.76 if path=='weapons/wooden/woodenbow.nif' else max(.76,min(.94,1-.7/(maximum+1.3)))
 coefficient=max(maximum+1.3,0)-max(minimum+1.3,0)
 base_width=maximum-minimum-base_depth*coefficient
 depth=max(0,base_depth-.4*base_width/coefficient) if coefficient>1e-9 else base_depth
 return depth

def build(source_dir,output_dir):
 source_dir=Path(source_dir).resolve();output_dir=Path(output_dir).resolve()
 if output_dir==source_dir or source_dir in output_dir.parents or output_dir in source_dir.parents:raise ValueError('Source and output directories must be separate, non-nested directories')
 reference=json.loads((ROOT/'reference_sources.json').read_text());rows=reference['meshes'];inputs=[]
 for row in rows:
  rel=Path(row['path']);assert not rel.is_absolute() and '..' not in rel.parts
  p=source_dir/rel
  if not p.is_file():raise FileNotFoundError(f'Missing original source mesh: {row["path"]}')
  data=p.read_bytes()
  if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError(f'Source does not match the supported reference: {row["path"]}')
  inputs.append((row,data))
 output_dir.mkdir(parents=True,exist_ok=True);package=output_dir/'package';reports=[]
 for row,data in inputs:
  for hand in ('left','right'):
   mesh=Mesh(data);parts=[]
   for d in mesh.parts:
    depth=cut_depth(d['part'].root_positions,hand,row['path'])
    effect='boundweapons' in row['path'] and mesh.objects[d['shape']].get('name') in ('FlamesMesh01:0','Refraction:0')
    parts.append(apply_window(d,hand,depth,influence_limit=.1 if effect else .01))
   result,changed=mesh.encode();digest=hashlib.sha256(result).hexdigest()
   if digest!=row['referenceOutputs'][hand]:raise ValueError(f'Generated mesh differs from verified 1.0 reference: {hand}/{row["path"]}')
   target=package/hand/'meshes'/row['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result)
   reports.append(dict(path=row['path'],hand=hand,sha256=digest,changedBlocks=changed,parts=parts))
 for name in ('ModuleConfig.xml','info.xml'):
  target=package/'fomod'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/'fomod'/name,target)
 shutil.copyfile(ROOT/'docs/local-mod-installation.txt',package/'README.txt')
 archive=output_dir/'BowSightWindows-VanillaDLC-MGO-1.0.0-FOMOD.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(package.rglob('*')):
   if p.is_file():
    info=zipfile.ZipInfo(p.relative_to(package).as_posix(),(2026,10,26,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None and len(z.namelist())==71
 report=dict(version='1.0.0',meshes=len(reports),shelfY=SHELF,topY=TOP,archiveSHA256=hashlib.sha256(archive.read_bytes()).hexdigest(),outputs=reports)
 (output_dir/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
 return archive

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-dir',type=Path,required=True,help='Folder containing the 34 original NIF paths from reference_sources.json');parser.add_argument('--output-dir',type=Path,default=ROOT/'build',help='Local output directory (ignored by Git)');args=parser.parse_args()
 print(build(args.source_dir,args.output_dir))
