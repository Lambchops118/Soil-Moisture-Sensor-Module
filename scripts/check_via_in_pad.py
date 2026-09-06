"""Report vias whose drill breaks into an SMD pad's soldermask aperture.

Rotation-aware: a pad's GetSize() is in the pad's own frame, so a 90/270-degree
pad has its extents swapped on the board. Comparing against an unrotated box gives
both false positives and false negatives.
"""
import math,sys
import pcbnew as p
def rect_pt(c,size,ang,q):
 t=math.radians(-ang);dx,dy=q[0]-c[0],q[1]-c[1]
 lx,ly=dx*math.cos(t)-dy*math.sin(t),dx*math.sin(t)+dy*math.cos(t)
 return math.hypot(max(abs(lx)-size[0]/2,0),max(abs(ly)-size[1]/2,0))
def scan(path):
 b=p.LoadBoard(path);out=[]
 for f in b.GetFootprints():
  for q in f.Pads():
   if q.GetAttribute()!=p.PAD_ATTRIB_SMD:continue
   c=p.ToMM(q.GetPosition());size=p.ToMM(q.GetSize());ang=q.GetOrientationDegrees()
   ep=f.GetReference()=='U4' and q.GetNumber() in ('9','')
   for t in b.Tracks():
    if not isinstance(t,p.PCB_VIA):continue
    dr=p.ToMM(t.GetDrill())/2;d=rect_pt(c,size,ang,p.ToMM(t.GetPosition()))
    if d<dr:out.append((round(dr-d,3),f.GetReference()+'.'+q.GetNumber(),
                        tuple(round(v,3) for v in p.ToMM(t.GetPosition())),t.GetNetname(),ep))
 return sorted(out,reverse=True)
if __name__=='__main__':
 for path,label in zip(sys.argv[1::2],sys.argv[2::2]):
  rows=scan(path);real=[r for r in rows if not r[4]]
  print(f'{label}: {len(real)} defects + {len(rows)-len(real)} intentional EP vias')
  for over,pad,pos,net,ep in rows:
   print(f'    {"EP  " if ep else "BAD "} {pad:<8} overlap {over:.3f}mm  {pos} {net}')
