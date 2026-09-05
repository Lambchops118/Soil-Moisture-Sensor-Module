"""Stitch isolated ground regions and remove obsolete routing stubs."""
exec(open('scripts/route_open.py').read().split('count=0')[0])
n=b.FindNet('/GND');blocked=mask(n.GetNetCode(),.515)
front=next(z for z in b.Zones() if z.IsOnLayer(p.F_Cu));back=next(z for z in b.Zones() if z.IsOnLayer(p.B_Cu));polys=front.GetFilledPolysList(p.F_Cu)
for k in range(1,polys.OutlineCount()):
 chain=polys.COutline(k);box=chain.BBox();x1,y1=mm(box.GetPosition());x2=x1+p.ToMM(box.GetWidth());y2=y1+p.ToMM(box.GetHeight());found=False
 for y in np.arange(y1+.31,y2-.3,.1):
  if found:break
  for x in np.arange(x1+.31,x2-.3,.1):
   xx,yy=ix(x,y);point=pos(float(x),float(y))
   if blocked[:,yy,xx].any() or not chain.PointInside(point) or not back.HitTestFilledArea(p.B_Cu,point):continue
   # Keep holes off surface-mount solder lands.
   if any(q.IsOnLayer(p.F_Cu) and q.GetBoundingBox().Contains(point) for f in b.GetFootprints() for q in f.Pads()):continue
   v=p.PCB_VIA(b);v.SetPosition(point);v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(n);b.Add(v);print('Stitched',k,round(x,3),round(y,3));found=True;break
 if not found:print('NO STITCH SITE',k)
# Consolidate near duplicate vias; do not leave drills that overlap.
vs=[t for t in b.GetTracks() if isinstance(t,p.PCB_VIA)];removed=set()
for i,a in enumerate(vs):
 if i in removed:continue
 for j,c in enumerate(vs[i+1:],i+1):
  if j in removed or a.GetNetCode()!=c.GetNetCode():continue
  if (a.GetPosition()-c.GetPosition()).EuclideanNorm()<p.FromMM(.55):
   for t in b.GetTracks():
    if isinstance(t,p.PCB_VIA) or t.GetNetCode()!=c.GetNetCode():continue
    if t.GetStart()==c.GetPosition():t.SetStart(a.GetPosition())
    if t.GetEnd()==c.GetPosition():t.SetEnd(a.GetPosition())
   b.RemoveNative(c);removed.add(j)
for v in report['violations']:
 if v['type'] in ['track_dangling','via_dangling']:
  q=objects.get(v['items'][0]['uuid'])
  if q and not any(q==vs[j] for j in removed):b.RemoveNative(q)
p.SaveBoard(str(path),b)
