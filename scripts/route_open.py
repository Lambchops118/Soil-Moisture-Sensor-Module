"""Conservative two-layer maze routing for DRC-reported open connections.

The routed result always requires KiCad's exact-geometry DRC afterwards.
Run with KiCad Python. Copper fills are ignored as routing obstacles.
"""
import pcbnew as p, json, math, heapq, time, sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]; path=ROOT/'hardware/SoilMoistureSensor.kicad_pcb'
b=p.LoadBoard(str(path)); report=json.loads((ROOT/'review/revB/drc.json').read_text())
step=.05; x0=95.;y0=47.; W=861;H=1451
layers=[p.F_Cu,p.B_Cu]
def ix(x,y):return (round((x-x0)/step),round((y-y0)/step))
def mm(v):return (p.ToMM(v.x),p.ToMM(v.y))
def pos(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
objects={str(q.m_Uuid.AsString()):q for f in b.GetFootprints() for q in f.Pads()}
objects.update({str(q.m_Uuid.AsString()):q for q in b.GetTracks()})
def mask(net,margin):
    ims=[Image.new('1',(W,H),0) for _ in range(2)]; ds=[ImageDraw.Draw(im) for im in ims]
    def rect(d,x1,y1,x2,y2):d.rectangle([ix(x1,y1),ix(x2,y2)],fill=1)
    for d in ds:
        rect(d,95,47,138,47.6);rect(d,95,47,95.6,119.5);rect(d,137.4,47,138,119.5)
        rect(d,107,47,126.5,58.7) # antenna copper keepout
    for f in b.GetFootprints():
        for q in f.Pads():
            if q.GetNetCode()==net:continue
            r=q.GetBoundingBox();a=mm(r.GetPosition());e=(a[0]+p.ToMM(r.GetWidth()),a[1]+p.ToMM(r.GetHeight()))
            for l,d in zip(layers,ds):
                if q.IsOnLayer(l):rect(d,a[0]-margin,a[1]-margin,e[0]+margin,e[1]+margin)
    for t in b.GetTracks():
        if t.GetNetCode()==net:continue
        a=mm(t.GetStart());c=mm(t.GetEnd());rad=p.ToMM(t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth())/2+margin
        for l,d in zip(layers,ds):
            if t.IsOnLayer(l):
                d.line([ix(*a),ix(*c)],fill=1,width=math.ceil(2*rad/step))
                for x,y in [a,c]:d.ellipse([ix(x-rad,y-rad),ix(x+rad,y+rad)],fill=1)
    return np.stack([np.array(im,dtype=bool) for im in ims])
def route(n,start,goal,sl,gl,width):
    net=n.GetNetCode(); block=mask(net,.215+width/2); vias=mask(net,.515)
    sx,sy=ix(*start);gx,gy=ix(*goal)
    if not (0<=sy<H and 0<=gy<H):return None
    starts=[l for l in sl if not block[l,sy,sx]]; goals=[l for l in gl if not block[l,gy,gx]]
    if not starts or not goals:return None
    def key(l,x,y):return l*W*H+y*W+x
    def decode(k):l,k=divmod(k,W*H);y,x=divmod(k,W);return l,x,y
    gkeys={key(l,gx,gy) for l in goals};scores={};parents={};heap=[]
    def heuristic(x,y):
        dx=abs(x-gx);dy=abs(y-gy);return max(dx,dy)+.41421356*min(dx,dy)
    for l in starts:
        k=key(l,sx,sy);scores[k]=0;heapq.heappush(heap,(heuristic(sx,sy),0,k))
    offsets=[(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.41421356),(1,-1,1.41421356),(-1,1,1.41421356),(-1,-1,1.41421356)]
    limit=time.monotonic()+45
    while heap:
        _,cost,k=heapq.heappop(heap)
        if cost>scores.get(k,1e30):continue
        if k in gkeys:
            path=[k]
            while k in parents:k=parents[k];path.append(k)
            return [decode(v) for v in reversed(path)]
        l,x,y=decode(k)
        for dx,dy,dist in offsets:
            xx=x+dx;yy=y+dy
            if xx<0 or yy<0 or xx>=W or yy>=H or block[l,yy,xx]:continue
            if dx and dy and (block[l,y,xx] or block[l,yy,x]):continue
            kk=key(l,xx,yy);cc=cost+dist
            if cc<scores.get(kk,1e30):scores[kk]=cc;parents[kk]=k;heapq.heappush(heap,(cc+heuristic(xx,yy)*1.04,cc,kk))
        if not vias[0,y,x] and not vias[1,y,x]:
            kk=key(1-l,x,y);cc=cost+80
            if cc<scores.get(kk,1e30):scores[kk]=cc;parents[kk]=k;heapq.heappush(heap,(cc+heuristic(x,y)*1.04,cc,kk))
        if len(scores)%10000==0 and time.monotonic()>limit:return None
    return None
def add(n,route,start,goal,width):
    # Collapse straight grid runs, keeping exact physical endpoints.
    pts=[route[0]]
    for i in range(1,len(route)-1):
        a,c,d=route[i-1:i+2]
        if (c[0]-a[0],c[1]-a[1],c[2]-a[2])!=(d[0]-c[0],d[1]-c[1],d[2]-c[2]):pts.append(c)
    pts.append(route[-1]);converted=[(l,x0+x*step,y0+y*step) for l,x,y in pts]
    converted.insert(0,(converted[0][0],*start));converted.append((converted[-1][0],*goal))
    for a,c in zip(converted,converted[1:]):
        if a[0]!=c[0]:
            v=p.PCB_VIA(b);v.SetPosition(pos(a[1],a[2]));v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNet(n);b.Add(v)
        elif a[1:]!=c[1:]:
            t=p.PCB_TRACK(b);t.SetStart(pos(*a[1:]));t.SetEnd(pos(*c[1:]));t.SetWidth(p.FromMM(width));t.SetLayer(layers[a[0]]);t.SetNet(n);b.Add(t)
count=0
for issue in report['unconnected_items']:
    a,c=issue['items'];qa=objects.get(a['uuid']);qc=objects.get(c['uuid'])
    if qa is None or qc is None:continue
    n=qa.GetNet();name=qa.GetNetname()
    if name.endswith('GND'):continue
    if len(sys.argv)>1 and sys.argv[1] not in name:continue
    start=(a['pos']['x'],a['pos']['y']);goal=(c['pos']['x'],c['pos']['y'])
    sl=[i for i,l in enumerate(layers) if qa.IsOnLayer(l)];gl=[i for i,l in enumerate(layers) if qc.IsOnLayer(l)]
    width=.4 if name.endswith('+3V3') else .35 if name.endswith('VBAT') else .25 if name.endswith(('VIN_DC','VSTOR','LBOOST')) else .2
    print('Route',name,start,goal,flush=True);r=route(n,start,goal,sl,gl,width)
    if r is None:
        print('  No path',flush=True);continue
    add(n,r,start,goal,width);count+=1;p.SaveBoard(str(path),b);print('  Routed',len(r),'steps',flush=True)
print('Completed',count,'routes',flush=True)

