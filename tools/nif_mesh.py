"""Bounded SSE skinned mesh editor. Unknown blocks remain opaque."""
from pathlib import Path
import struct,math
from nif_io import blocks,Reader,read_sse
def pack(fmt,*v):return struct.pack('<'+fmt,*v)
def norm(v):
 length=math.hypot(*v);return [x/length for x in v] if length>1e-9 else [0,0,1]
def identity():return ([1,0,0,0,1,0,0,0,1],[0,0,0],1)
def tf(values):return (list(values[:9]),list(values[9:12]),values[12])
def mv(R,p):return [sum(R[i*3+j]*p[j] for j in range(3)) for i in range(3)]
def trans(t,p):return [a*t[2]+b for a,b in zip(mv(t[0],p),t[1])]
def invtrans(t,p):return mv([t[0][j*3+i] for i in range(3) for j in range(3)],[(p[i]-t[1][i])/t[2] for i in range(3)])
def compose(a,b):
 return ([sum(a[0][i*3+k]*b[0][k*3+j] for k in range(3)) for i in range(3) for j in range(3)],trans(a,b[1]),a[2]*b[2])
def assemble(data,replacements):
 bs=blocks(data);r=Reader(data);r.take(data.index(b'\n')+1);_,_,_,n,_=r.values('IBIII')
 for _ in range(3):r.string(True)
 for _ in range(r.one('H')):r.string()
 r.take(n*2);sizeoff=r.pos;header=bytearray(data[:bs[0][1]])
 for i,b in replacements.items():struct.pack_into('<I',header,sizeoff+i*4,len(b))
 return bytes(header)+b''.join(replacements.get(i,b) for i,(_,_,b) in enumerate(bs))+data[bs[-1][1]+len(bs[-1][2]):]
class Partition:
 def __init__(self,b):
  r=Reader(b);self.n,self.size,self.stride,self.desc=r.values('IIIQ');assert self.n==1 and self.stride in (40,44),('unsupported partition',self.n,self.stride)
  self.raw=[bytearray(r.take(self.stride)) for _ in range(self.size//self.stride)]
  nv,nt,nb,ns,nw=r.values('5H');assert nv==len(self.raw) and ns==0 and nw==4
  self.bones=r.values('H'*nb)
  assert self.bones==tuple(range(nb)),'Nonidentity bone palettes require a separate SSE raw-index mapping implementation'
  assert r.one('B')==1;self.vmap=r.values('H'*nv);assert set(self.vmap)==set(range(nv))
  assert r.one('B')==1;wf=r.values('f'*(nv*4));assert r.one('B')==1;self.tri0=r.values('H'*(nt*3));assert r.one('B')==1;bi=r.take(nv*4);self.lod,self.glob,pdesc=r.values('BBQ');tc=r.values('H'*(nt*3));assert pdesc==self.desc and r.pos==len(b)
  self.triangles=[tuple(tc[i:i+3]) for i in range(0,len(tc),3)];self.copy=tc
  self.skin_off=((self.desc>>28)&15)*4;self.uv_off=((self.desc>>8)&15)*4;self.normal_off=((self.desc>>16)&15)*4;self.tangent_off=((self.desc>>20)&15)*4;self.color_off=((self.desc>>24)&15)*4
  assert self.skin_off in (28,32) and self.uv_off==16 and self.normal_off==20 and self.tangent_off==24
  self.vertices=[]
  for b in self.raw:
   so=self.skin_off
   self.vertices.append(dict(p=list(struct.unpack_from('<3f',b)),uv=list(struct.unpack_from('<2e',b,16)),n=[x/127.5-1 for x in b[20:23]],t=[x/127.5-1 for x in b[24:27]],bit=[struct.unpack_from('<f',b,12)[0],b[23]/127.5-1,b[27]/127.5-1],color=list(b[self.color_off:self.color_off+4]) if self.color_off else [],w={int(i):float(w) for i,w in zip(b[so+8:so+12],struct.unpack_from('<4e',b,so)) if w>0}))
  for local,globalid in enumerate(self.vmap):self.vertices[globalid]['w']={self.bones[bi[local*4+j]]:wf[local*4+j] for j in range(4) if wf[local*4+j]>0}
  self.original_count=nv;self.original_triangles=list(self.triangles)
 def encode(self):
  nv=len(self.raw);nt=len(self.triangles);nb=len(self.bones);assert nv<65536 and nt<65536
  flat=[i for t in self.triangles for i in t];tris=pack('H'*len(flat),*flat);wf=[];bi=[]
  for v in self.vertices:
   items=list(v['w'].items());assert len(items)<=4;items+=[(self.bones[0],0)]*(4-len(items));bi.extend(self.bones.index(i) for i,w in items);wf.extend(w for i,w in items)
  return pack('IIIQ',1,nv*self.stride,self.stride,self.desc)+b''.join(self.raw)+pack('5H',nv,nt,nb,0,4)+pack('H'*nb,*self.bones)+b'\1'+pack('H'*nv,*range(nv))+b'\1'+pack('f'*len(wf),*wf)+b'\1'+tris+b'\1'+bytes(bi)+pack('BBQ',self.lod,self.glob,self.desc)+tris
 def write_vertex(self,i,p,n,t,bit):
  v=self.vertices[i];old=self.raw[i];b=bytearray(old) if old is not None else bytearray(self.stride)
  struct.pack_into('<3f',b,0,*p);struct.pack_into('<2e',b,16,*v['uv']);to_byte=lambda x:max(0,min(255,round((x+1)*127.5)))
  b[20:23]=bytes(to_byte(x) for x in norm(n));b[24:27]=bytes(to_byte(x) for x in norm(t));bit=norm(bit);struct.pack_into('<f',b,12,bit[0]);b[23]=to_byte(bit[1]);b[27]=to_byte(bit[2])
  if old is None:
   if self.color_off:b[self.color_off:self.color_off+4]=bytes(max(0,min(255,round(x))) for x in v['color'])
   items=list(v['w'].items());items+=[(self.bones[0],0)]*(4-len(items));so=self.skin_off;struct.pack_into('<4e',b,so,*[w for i,w in items]);b[so+8:so+12]=bytes(self.bones.index(i) for i,w in items)
  self.raw[i]=b
class Mesh:
 def __init__(self,data):
  self.data=data;self.parsed=read_sse(data);self.bs=blocks(data);self.objects=self.parsed['objects'];self.parts=[]
  parents={c:o['index'] for o in self.objects for c in o.get('children',[])};cache={}
  def world(i):
   if i in cache:return cache[i]
   o=self.objects[i];local=(o.get('rotation',identity()[0]),o.get('translation',[0,0,0]),o.get('scale',1));cache[i]=compose(world(parents[i]),local) if i in parents else local;return cache[i]
  self.world=world
  self.mid=next((o for o in self.objects if o.get('name')=='Bow_MidBone'),None)
  for shape in self.objects:
   if 'TriShape' not in shape['type'] or shape.get('skin',-1)<0:continue
   si=shape['skin'];ir=Reader(self.bs[si][2]);skin,partition,root,n=ir.values('iiiI');refs=ir.values('i'*n);assert ir.pos==len(self.bs[si][2])
   part=Partition(self.bs[partition][2]);sr=Reader(self.bs[skin][2]);skinhead=sr.take(57);assert struct.unpack_from('<I',skinhead,52)[0]==n
   bone_data=[]
   for _ in range(n):
    tb=sr.take(68);count=sr.one('H');entries=[sr.values('Hf') for _ in range(count)] if skinhead[-1] else [];bone_data.append((tb,entries))
   assert sr.pos==len(self.bs[skin][2])
   index=refs.index(self.mid['index']) if self.mid and self.mid['index'] in refs else 0
   mapping=compose(world(refs[index]),tf(struct.unpack_from('<13f',bone_data[index][0])))
   part.root_positions=[trans(mapping,v['p']) for v in part.vertices]
   self.parts.append(dict(shape=shape['index'],skin=skin,partition=partition,part=part,skinhead=skinhead,bonedata=bone_data,mapping=mapping))
 def encode(self):
  replacements={}
  for d in self.parts:
   p=d['part']
   if not getattr(p,'changed',False):continue
   replacements[d['partition']]=p.encode();skin=bytearray(d['skinhead'])
   for bone,(tb,entries) in enumerate(d['bonedata']):
    entries=list(entries)+[(i,v['w'][bone]) for i,v in enumerate(p.vertices) if i>=p.original_count and bone in v['w']]
    skin+=tb+pack('H',len(entries))+b''.join(pack('Hf',i,w) for i,w in entries)
   replacements[d['skin']]=bytes(skin)
  return assemble(self.data,replacements),sorted(replacements)
