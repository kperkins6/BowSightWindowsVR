"""Reviewable local projects and transactional mesh-only output generation."""
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import tempfile
import zipfile

from build import cut_depth
from nif_io import blocks
from nif_mesh import Mesh, trans
from patcher_assets import MARKER, asset_path
from patcher_scan import assets_for, scan
from window import apply_window, SHELF, TOP, TAPER, BEVEL

VERSION='1.1.0-preview'
DEFAULTS=dict(shelf=SHELF,height=TOP-SHELF,taper=TOP-TAPER,bevel=BEVEL,
              inner=-1.3,depth=None,protect_string=True,shapes=None)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def settings(value):
    if not isinstance(value,dict) or set(value)-set(DEFAULTS): raise ValueError('Unknown window setting')
    result={**DEFAULTS,**value}
    for key in ('shelf','height','taper','bevel','inner'):
        x=result[key]
        if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or abs(x)>10000:
            raise ValueError('Invalid '+key)
    if not 0<result['bevel']<result['height']-result['taper']<result['height']:
        raise ValueError('Height must exceed taper plus bevel; all must be positive')
    depth=result['depth']
    if depth is not None and (isinstance(depth,bool) or not isinstance(depth,(int,float)) or not math.isfinite(depth) or not 0<depth<.99):
        raise ValueError('Depth must be between 0 and 0.99, or automatic')
    if type(result['protect_string']) is not bool: raise ValueError('Invalid string protection')
    shapes=result['shapes']
    if shapes is not None and (not isinstance(shapes,list) or not shapes or any(type(i) is not int or i<0 for i in shapes)):
        raise ValueError('Select at least one shape')
    return result


def area(points,t):
    a,b,c=[points[i] for i in t];u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    return math.hypot(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])


def check_rig(mesh):
    if not mesh.mid: raise ValueError('Unsupported rig: Bow_MidBone is missing')
    if not mesh.parts: raise ValueError('No supported SSE skinned bow geometry')
    points=[q for d in mesh.parts for q in d['part'].root_positions]
    if not points: raise ValueError('Empty bow geometry')
    span=[max(q[i] for q in points)-min(q[i] for q in points) for i in range(3)]
    if span[1] < 1.2*max(span[0],span[2]) or span[1]<20:
        raise ValueError('Unsupported orientation/scale: bow must extend along model Y in the Skyrim bow rig')


def patch(data, path, hand, options):
    options=settings(options);mesh=Mesh(data);check_rig(mesh);shapes=[];reports=[];warnings=[]
    selected=options['shapes']
    ids={d['shape'] for d in mesh.parts}
    if selected is not None and not set(selected)<=ids: raise ValueError('Selected shape does not exist')
    for d in mesh.parts:
        p=d['part'];name=mesh.objects[d['shape']].get('name','')
        before=[q[:] for q in p.root_positions];triangles=list(p.triangles)
        enabled=selected is None or d['shape'] in selected
        if enabled:
            depth=options['depth']
            if depth is None: depth=cut_depth(before,hand,path)
            effect=name in ('FlamesMesh01:0','Refraction:0')
            report=apply_window(d,hand,depth,influence_limit=.1 if effect else .01,profile=options)
            reports.append(report);after=p.preview_after
            if report['maximumDiscardedInfluence']:
                warnings.append(f'{name}: new edge vertices reduce bone influences by up to {report["maximumDiscardedInfluence"]:.1%}')
        else: after=before
        shapes.append(dict(id=d['shape'],name=name,editable=True,enabled=enabled,
                           before=before,after=after,triangles=p.triangles,beforeTriangles=triangles))
    # Include embedded unskinned geometry in both views so a decoration cannot
    # silently disappear from the preview while remaining in game.
    for obj in mesh.objects:
        if obj['index'] in ids: continue
        if obj.get('vertices'):
            _,_,block=mesh.bs[obj['index']]
            extras=struct.unpack_from('<I',block,4)[0]
            stride=(int(obj['vertex_desc'],16)&15)*4
            offset=116+extras*4+obj['vertex_count']*stride
            flat=struct.unpack_from('<'+'H'*(obj['triangles']*3),block,offset)
            triangles=[flat[i:i+3] for i in range(0,len(flat),3)]
            points=[trans(mesh.world(obj['index']),q) for q in obj['vertices']]
            shapes.append(dict(id=obj['index'],name=obj.get('name','static'),editable=False,enabled=False,
                               before=points,after=points,triangles=triangles,beforeTriangles=triangles))
            warnings.append('Static shape retained without editing: '+obj.get('name','unnamed'))
        elif 'TriShape' in obj['type'] or 'TriStrips' in obj['type']:
            warnings.append('Preview cannot display unsupported geometry block: '+obj['type']+' '+obj.get('name',''))
    output,changed=mesh.encode()
    count=sum(r['changedVertices'] for r in reports)
    if not count: raise ValueError('Opening does not intersect selected bow geometry; adjust shelf, depth or shapes')
    # Reparse the bytes that will actually be installed, and validate them.
    parsed=Mesh(output)
    for original,generated in zip(mesh.parts,parsed.parts):
        p=generated['part'];positions=p.root_positions
        if not all(math.isfinite(x) for q in positions for x in q): raise ValueError('Nonfinite output vertex')
        if any(len(set(t))!=3 or min(t)<0 or max(t)>=len(positions) for t in p.triangles): raise ValueError('Invalid output triangle')
        old=original['part']
        bound=parsed.objects[generated['shape']]['bound']
        if not all(math.isfinite(x) for x in bound) or bound[3]<0: raise ValueError('Invalid original shape bound')
        old_overshoot=max(math.dist(v['p'],bound[:3])-bound[3] for v in old.vertices[:old.original_count])
        new_overshoot=max(math.dist(v['p'],bound[:3])-bound[3] for v in p.vertices)
        if new_overshoot>max(.002,old_overshoot+.002): raise ValueError('Opening exceeds original mesh bounds; reduce depth or inner boundary')
        old_degenerate=sum(area(old.root_positions,t)<1e-10 for t in old.original_triangles)
        if sum(area(positions,t)<1e-10 for t in p.triangles)>old_degenerate: raise ValueError('Cut creates degenerate triangles; adjust the opening')
        for v in p.vertices:
            if not all(math.isfinite(x) for x in v['p']+v['uv']): raise ValueError('Nonfinite vertex attribute')
            if any(not math.isfinite(w) or w<0 for w in v['w'].values()) or not .98<sum(v['w'].values())<1.02:
                raise ValueError('Invalid output skin weights')
        # Use serialized/quantized geometry in the right-hand viewer.
        shape=next(s for s in shapes if s['id']==generated['shape'])
        shape['after']=positions;shape['triangles']=p.triangles
    original_blocks=blocks(data);new_blocks=blocks(output)
    for i,(kind,_,blob) in enumerate(original_blocks):
        if i not in changed and blob!=new_blocks[i][2]: raise ValueError('Unexpected change to opaque block '+kind)
    return output,dict(shapes=shapes,reports=reports,warnings=warnings,changedVertices=count,sha256=digest(output))


class Project:
    def __init__(self,inventory,hand='left'):
        if hand not in ('left','right'): raise ValueError('Invalid hand')
        self.inventory=copy.deepcopy(inventory);self.hand=hand
        self.assets=assets_for(inventory);self.rows=copy.deepcopy(inventory['bows'])
        self.previews={}
        for row in self.rows:
            row.update(settings=copy.deepcopy(DEFAULTS),approved=False,include=True)
            row['supported']=False
            if row.get('error'): continue
            try:
                data=self.read(row);mesh=Mesh(data);check_rig(mesh)
                row['supported']=True
                row['shapeNames']=[dict(id=d['shape'],name=mesh.objects[d['shape']].get('name','')) for d in mesh.parts]
            except (ValueError,AssertionError,IndexError,KeyError,struct.error,OSError,RecursionError) as e:
                row['error']=str(e) or type(e).__name__

    def row(self,key):
        return next(r for r in self.rows if r['id']==key)

    def read(self,row):
        data,source=self.assets.read('meshes/'+asset_path(row['path']))
        if source!=row.get('source') or digest(data)!=row.get('sha256'): raise ValueError('Source changed since scan; rescan the mod list')
        return data

    def stamp(self,row):
        return digest(json.dumps([row['sha256'],row['source'],self.hand,row['settings']],sort_keys=True).encode())

    def set_hand(self,hand):
        if hand not in ('left','right'): raise ValueError('Invalid hand')
        if hand!=self.hand:
            self.hand=hand;self.previews.clear()
            for row in self.rows: row['approved']=False

    def update(self,key,options=None,include=None):
        row=self.row(key)
        if options is not None:
            value=settings({**row['settings'],**options})
            if value!=row['settings']:
                row['settings']=value;row['approved']=False;self.previews.pop(key,None)
        if include is not None:
            if type(include) is not bool: raise ValueError('Invalid inclusion choice')
            row['include']=include
            if not include: row['approved']=False
        return row

    def preview(self,key):
        row=self.row(key)
        if not row['supported']: raise ValueError(row.get('error','Unsupported mesh'))
        stamp=self.stamp(row);cached=self.previews.get(key)
        if cached and cached[0]==stamp: return cached[2]
        output,preview=patch(self.read(row),row['path'],self.hand,row['settings'])
        self.previews[key]=(stamp,output,preview)
        return preview

    def approve(self,key):
        row=self.row(key);cached=self.previews.get(key)
        if not cached or cached[0]!=self.stamp(row): raise ValueError('Generate a current preview before approving')
        self.read(row)
        row['approved']=True;row['include']=True

    def batch(self,keys,action,options=None):
        if not isinstance(keys,list) or not keys or len(keys)>10000 or any(not isinstance(k,str) for k in keys):
            raise ValueError('Select one or more bows')
        known={r['id']:r for r in self.rows}
        if any(k not in known for k in keys): raise ValueError('Batch contains an unknown bow')
        rows=[known[k] for k in dict.fromkeys(keys)]
        if action not in ('settings','approve','include','skip'): raise ValueError('Unknown batch action')
        eligible=[r for r in rows if r['supported']] if action in ('settings','approve') else rows
        if not eligible: raise ValueError('No supported bows in this selection')
        if action=='settings':
            if not isinstance(options,dict): raise ValueError('Missing batch settings')
            # Shape IDs belong to an individual NIF, so never transfer them.
            options={k:v for k,v in options.items() if k!='shapes'}
            for row in eligible: settings({**row['settings'],**options})
        if action=='approve':
            for row in eligible:
                cached=self.previews.get(row['id'])
                if not cached or cached[0]!=self.stamp(row): raise ValueError('Every selected supported bow needs a current preview')
                self.read(row)
        for row in eligible:
            if action=='settings': self.update(row['id'],options)
            elif action=='approve': self.approve(row['id'])
            else: self.update(row['id'],include=action=='include')
        return dict(affected=len(eligible),unsupported=len(rows)-len(eligible))

    def summary(self):
        return dict(hand=self.hand,rows=self.rows,warnings=self.inventory['warnings'],config=self.inventory['config'],
                    weaponCount=self.inventory['weaponCount'],pluginCount=self.inventory['pluginCount'])

    def document(self):
        return dict(format='BowSightProject',version=1,config=self.inventory['config'],hand=self.hand,rows=copy.deepcopy(self.rows))

    @classmethod
    def restore(cls,document,progress=None):
        if document.get('format')!='BowSightProject' or document.get('version')!=1: raise ValueError('Unsupported project file')
        project=cls(scan(document['config'],progress),document['hand'])
        saved={r['path']:r for r in document['rows']}
        for row in project.rows:
            old=saved.get(row['path'])
            if not old: continue
            project.update(row['id'],old['settings'],old.get('include',True))
            if row['supported'] and old.get('approved') and old.get('sha256')==row.get('sha256') and old.get('source')==row.get('source'):
                project.preview(row['id']);project.approve(row['id'])
        return project

    def generate(self,output,make_zip=True):
        if not str(output).strip(): raise ValueError('Choose a new output folder')
        output=Path(output).resolve()
        if output.suffix.lower()=='.zip': raise ValueError('Choose an output folder name without the .zip extension')
        if output.exists() or output.with_suffix('.zip').exists(): raise ValueError('Output folder or ZIP already exists; choose a new name')
        inputs=[Path(p).resolve() for p in self.inventory['roots']]
        inputs.extend(Path(self.inventory['config'][key]).resolve() for key in ('mo2','plugins','loadorder') if self.inventory['config'].get(key))
        for source in inputs:
            if output==source or source in output.parents or output in source.parents:
                raise ValueError('Output must be separate from input/source folders; nested paths are forbidden')
        selected=[r for r in self.rows if r['include'] and r['supported']]
        if not selected: raise ValueError('No supported bows selected')
        if any(not r['approved'] for r in selected): raise ValueError('Every included supported bow needs review; approve or skip it first')
        # Refresh file priorities, not only file bytes: a newly added higher
        # priority override must invalidate the earlier review too.
        self.assets=assets_for(self.inventory)
        for path,snapshot in {**self.inventory.get('pluginSnapshots',{}),**self.inventory['config'].get('_selectionSnapshots',{})}.items():
            p=Path(path)
            if not p.is_file() or [p.stat().st_size,p.stat().st_mtime_ns]!=snapshot:
                raise ValueError('Active plugin changed since scan; rescan the mod list')
        generated=[]
        for row in selected:
            data=self.read(row)
            # Regenerate and verify equality to the exact reviewed bytes.
            result,preview=patch(data,row['path'],self.hand,row['settings'])
            cached=self.previews.get(row['id'])
            if not cached or cached[0]!=self.stamp(row) or cached[1]!=result: raise ValueError('Review no longer matches output; preview again')
            generated.append((row,result,preview['sha256']))
        output.parent.mkdir(parents=True,exist_ok=True)
        # The temporary staging tree is confined to the chosen output parent.
        with tempfile.TemporaryDirectory(prefix='.bow-sight-stage-',dir=output.parent) as temp:
            stage=Path(temp);mod=stage/'mod';mod.mkdir()
            entries=[]
            for row,result,sha in generated:
                target=mod/'meshes'/asset_path(row['path']);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result)
                entries.append(dict(path=row['path'],source=row['source'],sourceSHA256=row['sha256'],sha256=sha,settings=row['settings']))
            manifest=dict(tool='Bow Sight Patcher',version=VERSION,hand=self.hand,meshes=entries,
                          skipped=[r['path'] for r in self.rows if not r['include'] or not r['supported']])
            (mod/MARKER).write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
            (mod/'README.txt').write_text('Bow Sight Patcher output\nHandedness: '+self.hand+'\nInstall this folder as a separate mod after the source meshes. No plugin is required.\n',encoding='utf-8')
            archive=stage/'mod.zip'
            if make_zip:
                with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
                    for p in sorted(mod.rglob('*')):
                        if p.is_file(): z.write(p,p.relative_to(mod).as_posix())
                with zipfile.ZipFile(archive) as z:
                    if z.testzip(): raise ValueError('ZIP validation failed')
            # Rename within the destination volume, after every mesh succeeds.
            mod.rename(output)
            if make_zip:
                try: archive.rename(output.with_suffix('.zip'))
                except OSError:
                    # Roll back our own newly published tree to private staging.
                    output.rename(mod)
                    raise
        return dict(path=str(output),zip=str(output.with_suffix('.zip')) if make_zip else None,count=len(entries),hand=self.hand)
