"""Move vias that sit inside SMD pads out to clear copper.

A via inside a pad's soldermask aperture wicks solder out of the joint during
reflow; every barrel here (0.3mm drill through 1.6mm board) holds more solder than
the joint it sits in. The two vias in U4's exposed thermal pad are deliberate and
are left alone. Each via is moved the shortest distance that clears its pad, every
other net, both hole-to-hole spacing and the keepout areas (including U2's antenna
region, which is a footprint-level rule area); its existing tracks are re-anchored
and a fresh F.Cu stub reconnects it to the pad.

Run with KiCad 10's bin/python.exe.
"""
from pathlib import Path
import math,shutil
import pcbnew as p

ROOT=Path(__file__).resolve().parents[1];HW=ROOT/'hardware'
PCB=HW/'SoilMoistureSensor.kicad_pcb'
CLR=0.2;HOLE=0.25
# U4's exposed thermal pad: vias in an EP are deliberate and must stay.
KEEP=lambda f,q:f.GetReference()=='U4' and q.GetNumber() in ('9','')
mm=p.ToMM;pt=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
R=lambda v:tuple(round(x,4) for x in mm(v))

def seg_pt(a,z,q):
 dx,dy=z[0]-a[0],z[1]-a[1];L=dx*dx+dy*dy
 t=0.0 if L==0 else max(0.0,min(1.0,((q[0]-a[0])*dx+(q[1]-a[1])*dy)/L))
 return math.hypot(q[0]-a[0]-t*dx,q[1]-a[1]-t*dy)
def seg_seg(a,z,c,d):
 cross=lambda o,u,v:(u[0]-o[0])*(v[1]-o[1])-(u[1]-o[1])*(v[0]-o[0])
 if ((cross(c,d,a)>0)!=(cross(c,d,z)>0)) and ((cross(a,z,c)>0)!=(cross(a,z,d)>0)):return 0.0
 return min(seg_pt(a,z,c),seg_pt(a,z,d),seg_pt(c,d,a),seg_pt(c,d,z))
def rect_pt(c,size,ang,q):
 t=math.radians(-ang);dx,dy=q[0]-c[0],q[1]-c[1]
 lx,ly=dx*math.cos(t)-dy*math.sin(t),dx*math.sin(t)+dy*math.cos(t)
 return math.hypot(max(abs(lx)-size[0]/2,0),max(abs(ly)-size[1]/2,0))
def poly_pt(poly,q):
 inside=False;n=len(poly)
 for i in range(n):
  (x1,y1),(x2,y2)=poly[i],poly[(i+1)%n]
  if (y1>q[1])!=(y2>q[1]) and q[0]<x1+(q[1]-y1)*(x2-x1)/(y2-y1):inside=not inside
 return 0.0 if inside else min(seg_pt(poly[i],poly[(i+1)%n],q) for i in range(n))
def poly_seg(poly,a,z):
 if poly_pt(poly,a)==0 or poly_pt(poly,z)==0:return 0.0
 n=len(poly);return min(seg_seg(a,z,poly[i],poly[(i+1)%n]) for i in range(n))

b=p.LoadBoard(str(PCB))
rules=[]   # keepouts, including footprint-level ones such as U2's antenna region
for z in list(b.Zones())+[q for f in b.GetFootprints() for q in f.Zones()]:
 if not z.GetIsRuleArea() or not (z.GetDoNotAllowVias() or z.GetDoNotAllowTracks()):continue
 o=z.Outline()
 for j in range(o.OutlineCount()):
  c=o.COutline(j)
  rules.append(([ (mm(c.CPoint(i).x),mm(c.CPoint(i).y)) for i in range(c.PointCount()) ],
                set(z.GetLayerSet().Seq()),z.GetDoNotAllowVias(),z.GetDoNotAllowTracks()))
holes=[]   # hole-to-hole spacing ignores nets entirely; keyed by position
for t in b.Tracks():
 if isinstance(t,p.PCB_VIA):holes.append([R(t.GetPosition()),mm(t.GetDrill())/2])
for f in b.GetFootprints():
 for q in f.Pads():
  if q.GetDrillSize().x:holes.append([R(q.GetPosition()),mm(q.GetDrillSize())[0]/2])

targets=[]
for f in b.GetFootprints():
 for q in f.Pads():
  if q.GetAttribute()!=p.PAD_ATTRIB_SMD:continue
  name=f.GetReference()+'.'+q.GetNumber()
  if KEEP(f,q):continue
  c=R(q.GetPosition());size=mm(q.GetSize());ang=q.GetOrientationDegrees()
  for t in b.Tracks():
   if not isinstance(t,p.PCB_VIA):continue
   # The barrel only drains the joint if the drill breaks into the pad's mask
   # aperture; a via whose annulus merely touches the pad is dammed by mask.
   # rect_pt is rotation-aware: GetSize() is in the pad's own frame, so a 90 or
   # 270-degree pad has its extents swapped on the board.
   if rect_pt(c,size,ang,R(t.GetPosition()))<mm(t.GetDrill())/2:targets.append((name,q,t))
assert targets,'Already applied'
backup=ROOT/'review/before-via-fix';backup.mkdir(exist_ok=True)
for path in [PCB,HW/'SoilMoistureSensor.kicad_sch']:shutil.copy2(path,backup/path.name)
print(len(targets),'vias to relocate')

def obstacles(skip_net,skip_ids):
 out=[]
 for t in b.Tracks():
  if id(t) in skip_ids or t.GetNetCode()==skip_net:continue
  if isinstance(t,p.PCB_VIA):out.append(('via',R(t.GetPosition()),mm(t.GetWidth(p.F_Cu))/2,None))
  else:out.append(('trk',(R(t.GetStart()),R(t.GetEnd())),mm(t.GetWidth())/2,t.GetLayer()))
 for f in b.GetFootprints():
  for q in f.Pads():
   if q.GetNetCode()==skip_net:continue
   out.append(('pad',(R(q.GetPosition()),mm(q.GetSize()),q.GetOrientationDegrees()),0,None))
 return out

def dist(item,q):
 kind,geo,hw,_=item
 if kind=='via':return math.hypot(q[0]-geo[0],q[1]-geo[1])
 if kind=='trk':return seg_pt(geo[0],geo[1],q)
 return rect_pt(geo[0],geo[1],geo[2],q)

def via_ok(pos,rad,drill,obs,skip_hole):
 for it in obs:
  if dist(it,pos)<rad+it[2]+CLR:return False
  if dist(it,pos)<drill+it[2]+HOLE:return False
 for hp,hr in holes:
  if hp==skip_hole:continue
  if math.hypot(pos[0]-hp[0],pos[1]-hp[1])<drill+hr+HOLE:return False
 for poly,layers,noV,_ in rules:
  if noV and (p.F_Cu in layers or p.B_Cu in layers) and poly_pt(poly,pos)<rad+CLR:return False
 return True

def seg_ok(a,z,hw,layer,obs):
 for kind,geo,ohw,olayer in obs:
  if kind=='trk':
   if olayer!=layer:continue
   d=seg_seg(a,z,geo[0],geo[1])
  elif kind=='via':d=seg_pt(a,z,geo)
  else:
   if layer!=p.F_Cu:continue
   d=min(rect_pt(geo[0],geo[1],geo[2],a),rect_pt(geo[0],geo[1],geo[2],z),
         rect_pt(geo[0],geo[1],geo[2],((a[0]+z[0])/2,(a[1]+z[1])/2)))
  if d<hw+ohw+CLR:return False
 for poly,layers,_,noT in rules:
  if noT and layer in layers and poly_seg(poly,a,z)<hw+CLR:return False
 return True

moved=[]
for name,pad,via in targets:
 pc=R(pad.GetPosition());psz=mm(pad.GetSize());pang=pad.GetOrientationDegrees()
 rad=mm(via.GetWidth(p.F_Cu))/2;drill=mm(via.GetDrill())/2;old=R(via.GetPosition())
 attached=[t for t in b.Tracks() if not isinstance(t,p.PCB_VIA) and (R(t.GetStart())==old or R(t.GetEnd())==old)]
 obs=obstacles(via.GetNetCode(),{id(x) for x in attached}|{id(via)})
 far=lambda t:(R(t.GetEnd()) if R(t.GetStart())==old else R(t.GetStart()))
 esc=[math.atan2(far(t)[1]-old[1],far(t)[0]-old[0]) for t in attached if far(t)!=old]
 stub_w=(max(mm(t.GetWidth()) for t in attached)/2) if attached else 0.125
 # Two cases. A via whose centre is inside the pad has to be lifted out and given a
 # fresh stub. A via that merely grazes the mask aperture from outside already has a
 # track to the pad, so it only needs the smallest nudge that clears the barrel.
 inside=rect_pt(pc,psz,pang,old)==0
 origin=pc if inside else old
 best=None
 for step in range(1,81):
  r=0.05*step
  for deg in range(0,360,5):
   th=math.radians(deg);cand=(round(origin[0]+r*math.cos(th),4),round(origin[1]+r*math.sin(th),4))
   if rect_pt(pc,psz,pang,cand)<max(rad+CLR,drill+HOLE,drill+0.05) if inside else       rect_pt(pc,psz,pang,cand)<drill+0.05:continue
   if not via_ok(cand,rad,drill,obs,old):continue
   if inside and not seg_ok(pc,cand,stub_w,p.F_Cu,obs):continue
   if not all(seg_ok(cand,far(t),mm(t.GetWidth())/2,t.GetLayer(),obs) for t in attached if far(t)!=old):continue
   pen=min((abs(math.atan2(math.sin(th-e),math.cos(th-e))) for e in esc),default=0)
   if best is None or (r,pen)<best[0]:best=((r,pen),cand)
  if best:break
 if best is None:
  # Report which constraint actually blocked, rather than failing blind.
  tally={}
  for step in range(1,81):
   for deg in range(0,360,5):
    r=0.05*step;th=math.radians(deg)
    cand=(round(origin[0]+r*math.cos(th),4),round(origin[1]+r*math.sin(th),4))
    lim=max(rad+CLR,drill+HOLE,drill+0.05) if inside else drill+0.05
    if rect_pt(pc,psz,pang,cand)<lim:k='own pad aperture'
    elif not via_ok(cand,rad,drill,obs,old):k='via body/hole clearance'
    elif inside and not seg_ok(pc,cand,stub_w,p.F_Cu,obs):k='new F.Cu stub blocked'
    elif not all(seg_ok(cand,far(t),mm(t.GetWidth())/2,t.GetLayer(),obs) for t in attached if far(t)!=old):k='re-anchored track blocked'
    else:k='CLEAR'
    tally[k]=tally.get(k,0)+1
  raise AssertionError('no clear position for %s; %r'%(name,sorted(tally.items(),key=lambda x:-x[1])))
 new=best[1]
 for t in attached:
  if R(t.GetStart())==old:t.SetStart(pt(*new))
  if R(t.GetEnd())==old:t.SetEnd(pt(*new))
 via.SetPosition(pt(*new))
 for h in holes:
  if h[0]==old:h[0]=new;break
 if inside:
  track=p.PCB_TRACK(b);track.SetStart(pad.GetPosition());track.SetEnd(pt(*new))
  track.SetWidth(p.FromMM(stub_w*2));track.SetLayer(p.F_Cu);track.SetNet(via.GetNet());b.Add(track)
 moved.append((name,old,new,math.dist(old,new)))
 print(f"  {name:<8} {'lift ' if inside else 'nudge'} {old} -> {new}  {math.dist(old,new):.2f}mm")

dead=[t for t in b.Tracks() if not isinstance(t,p.PCB_VIA) and R(t.GetStart())==R(t.GetEnd())]
for t in dead:b.Remove(t)
print('removed',len(dead),'zero-length tracks')
filler=p.ZONE_FILLER(b);filler.Fill(b.Zones());p.SaveBoard(str(PCB),b)
text=PCB.read_text(encoding='utf8')
with open(PCB,'w',encoding='utf8',newline='') as out:out.write(text.replace('\r\n','\n').replace('\n','\r\n'))
print('relocated',len(moved),'vias; max move',round(max(m[3] for m in moved),3),'mm')
