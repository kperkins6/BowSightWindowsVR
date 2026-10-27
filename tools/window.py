"""Add localized support loops and shape one side of the bow's sight window."""
import math,struct
from nif_mesh import norm,mv,trans,invtrans
SHELF=3.9707460691833494
TOP=17.595611910377503
TAPER=12.495611910377502
BEVEL=.2125
def apply_window(d,hand,depth=.76,influence_limit=.01):
 p=d['part'];mapping=d['mapping'];sign=1 if hand=='left' else -1;verts=p.vertices;roots=p.root_positions;cache={};changed=[];discarded=[]
 # String triangles are separate islands. Protect their complete islands rather
 # than using an X cutoff, which can stretch ornate bow decorations into spikes.
 parents=list(range(len(verts)))
 def find(i):
  while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
  return i
 for a,b,c in p.triangles:
  parents[find(b)]=find(a);parents[find(c)]=find(a)
 islands={}
 for i in range(len(verts)):islands.setdefault(find(i),[]).append(i)
 protected=set()
 for ids in islands.values():
  if all(roots[i][0]<-9 and abs(roots[i][2]+.0198)<.25 for i in ids):protected.update(ids)
 def edge(a,b,y):
  key=(min(a,b),max(a,b),y)
  if key in cache:return cache[key]
  u=(y-roots[a][1])/(roots[b][1]-roots[a][1]);v={}
  for k in ('p','uv','n','t','bit','color'):v[k]=[x+(z-x)*u for x,z in zip(verts[a][k],verts[b][k])]
  wa,wb=verts[a]['w'],verts[b]['w'];w={i:wa.get(i,0)*(1-u)+wb.get(i,0)*u for i in set(wa)|set(wb)};w={i:x for i,x in w.items() if x>1e-7}
  if len(w)>4:
   ranked=sorted(w.items(),key=lambda item:-item[1]);dropped=sum(x for i,x in ranked[4:]);assert dropped<influence_limit,('significant bone influence truncation',dropped);discarded.append(dropped);w=dict(ranked[:4])
  total=sum(w.values());v['w']={i:x/total for i,x in w.items()};root=[x+(z-x)*u for x,z in zip(roots[a],roots[b])];root[1]=y
  cache[key]=len(verts)
  if a in protected and b in protected:protected.add(cache[key])
  verts.append(v);roots.append(root);p.raw.append(None);return cache[key]
 def clip(t,y,up):
  out=[]
  for a,b in zip(t,t[1:]+t[:1]):
   ya,yb=roots[a][1],roots[b][1];ina=ya>=y if up else ya<=y;inb=yb>=y if up else yb<=y
   if ina:out.append(a)
   if ina!=inb and abs(ya-y)>1e-7 and abs(yb-y)>1e-7:out.append(edge(a,b,y))
  return out
 for y in (SHELF,SHELF+BEVEL,TAPER,TOP):
  result=[]
  for t in p.triangles:
   ps=[roots[i] for i in t]
   if all(i in protected for i in t) or not min(q[1] for q in ps)<y<max(q[1] for q in ps):result.append(t);continue
   for up in (False,True):
    poly=clip(list(t),y,up)
    result.extend((poly[0],poly[i],poly[i+1]) for i in range(1,len(poly)-1))
  p.triangles=result
 R=mapping[0];RT=[R[j*3+i] for i in range(3) for j in range(3)];after=[]
 for i,v in enumerate(verts):
  x,y,z=roots[i];f=df=0
  if SHELF<y<TOP and i not in protected and sign*z>-1.3:
   if y<SHELF+BEVEL:f=(y-SHELF)/BEVEL;df=1/BEVEL
   elif y<=TAPER:f=1
   else:f=(TOP-y)/(TOP-TAPER);df=-1/(TOP-TAPER)
  new=[x,y,z-sign*depth*f*(sign*z+1.3)];after.append(new)
  moved=math.dist(new,roots[i])>1e-7
  if moved:changed.append(i)
  if i<p.original_count and not moved:continue
  jy=-sign*depth*df*(sign*z+1.3);jz=1-depth*f
  n=mv(R,v['n']);t=mv(R,v['t']);bit=mv(R,v['bit'])
  n=[n[0],n[1]-jy*n[2]/jz,n[2]/jz];t=[t[0],t[1],jy*t[1]+jz*t[2]];bit=[bit[0],bit[1],jy*bit[1]+jz*bit[2]]
  p.write_vertex(i,invtrans(mapping,new),mv(RT,n),mv(RT,t),mv(RT,bit))
 p.changed=bool(changed);p.preview_before=roots;p.preview_after=after
 return dict(originalVertices=p.original_count,vertices=len(verts),originalTriangles=len(p.original_triangles),triangles=len(p.triangles),changedVertices=len(changed),depth=depth,shelfY=SHELF,topY=TOP,taperY=TAPER,protectedStringVertices=len(protected),newEdgesWithReducedBoneInfluences=len(discarded),maximumDiscardedInfluence=max(discarded,default=0))
