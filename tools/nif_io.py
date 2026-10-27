"""Bounded read-only SSE NIF subset. No exporter or asset modifications.

Field order follows the niftools/nifxml SSE definitions.
Only Bethesda stream 100 with 20.2.0.7 is accepted. Unknown blocks stay opaque.
"""
import math
import struct

class Reader:
    def __init__(self,data):self.data=data;self.pos=0
    def take(self,n):
        if n<0 or self.pos+n>len(self.data):raise ValueError('truncated NIF field')
        result=self.data[self.pos:self.pos+n];self.pos+=n;return result
    def values(self,fmt):return struct.unpack('<'+fmt,self.take(struct.calcsize('<'+fmt)))
    def one(self,fmt):return self.values(fmt)[0]
    def string(self,short=False):
        n=self.one('B' if short else 'I')
        if n>65536:raise ValueError('oversized string')
        return self.take(n).rstrip(b'\0').decode('utf-8',errors='replace')
    def count(self,maximum=65536):
        n=self.one('I')
        if n>maximum:raise ValueError('oversized array')
        return n

def read_sse(data):
    if len(data)>16*1024*1024:raise ValueError('audit file limit')
    r=Reader(data)
    end=data.find(b'\n',0,100)
    if end<0 or not data.startswith(b'Gamebryo File Format, Version 20.2.0.7'):raise ValueError('unsupported header')
    r.take(end+1)
    version,endian,user,count,stream=r.values('IBIII')
    if (version,endian,user,stream)!=(0x14020007,1,12,100) or count>65536:raise ValueError('unsupported stream')
    exports=[r.string(True) for _ in range(3)]
    types=[r.string() for _ in range(r.one('H'))]
    type_indices=r.values('H'*count);sizes=r.values('I'*count)
    strings_count=r.count();max_string=r.count()
    strings=[r.string() for _ in range(strings_count)]
    if any(len(s.encode('utf-8'))>max_string for s in strings):raise ValueError('string limit mismatch')
    r.take(r.count()*4)
    objects=[]
    for index,(type_index,size) in enumerate(zip(type_indices,sizes)):
        if type_index>=len(types):raise ValueError('unknown type index')
        kind=types[type_index];block=r.take(size);obj={'index':index,'type':kind,'bytes':size}
        if kind in ('NiNode','BSFadeNode','BSTriShape','BSSubIndexTriShape','BSMeshLODTriShape'):
            b=Reader(block);name=b.one('I');extra=b.count();b.take(extra*4)
            controller,flags=b.values('iI');pose=b.values('13f');collision=b.one('i')
            if not all(math.isfinite(v) for v in pose):raise ValueError('nonfinite node pose')
            if name!=0xffffffff and name>=len(strings):raise ValueError('unknown string index')
            obj.update(name='' if name==0xffffffff else strings[name],controller=controller,flags=flags,translation=pose[:3],rotation=pose[3:12],scale=pose[12],collision=collision)
            if kind in ('NiNode','BSFadeNode'):
                children=b.count();obj['children']=b.values('i'*children);b.take(b.count()*4)
                if b.pos!=len(block):raise ValueError('unparsed node fields')
            else:
                bound=b.values('4f');skin,shader,alpha,desc,triangles,vertices,data_size=b.values('iiiQHHI')
                stride=(desc&15)*4
                obj.update(bound=bound,skin=skin,shader=shader,alpha=alpha,vertex_desc=hex(desc),vertex_count=vertices,triangles=triangles,vertices=[])
                if data_size:
                    if not(desc>>44&1) or stride<16 or data_size!=vertices*stride+triangles*6:raise ValueError('unsupported vertex data')
                    packed=b.take(vertices*stride)
                    positions=[struct.unpack_from('<3f',packed,j*stride) for j in range(vertices)]
                    if not all(math.isfinite(x) for p in positions for x in p):raise ValueError('nonfinite vertex')
                    obj['vertices']=positions;b.take(triangles*6)
                # Particle arrays are optional and separate from the rendered vertices.
                particles=b.one('I')
                if particles:b.take(vertices*12+triangles*6)
                if kind=='BSTriShape' and b.pos!=len(block):raise ValueError('unparsed tri-shape fields')
        objects.append(obj)
    roots=r.values('i'*r.count())
    if any(i<0 or i>=count for i in roots) or r.pos!=len(data):raise ValueError('invalid footer')
    return dict(version=version,stream=stream,exports=exports,strings=strings,objects=objects,roots=list(roots))


def blocks(data):
 r=Reader(data);r.take(data.index(b'\n')+1);_,_,_,n,_=r.values('IBIII')
 for _ in range(3):r.string(True)
 types=[r.string() for _ in range(r.one('H'))];ids=r.values('H'*n);sizes=r.values('I'*n)
 ns=r.one('I');r.one('I')
 for _ in range(ns):r.string()
 r.take(r.one('I')*4);out=[]
 for t,size in zip(ids,sizes):
  start=r.pos;out.append((types[t],start,r.take(size)))
 return out
