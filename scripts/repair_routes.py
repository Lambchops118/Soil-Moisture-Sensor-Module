from pathlib import Path
import pcbnew as p,json
R=Path(__file__).resolve().parents[1];path=R/'hardware/SoilMoistureSensor.kicad_pcb'
b=p.LoadBoard(str(path));fs={f.GetReference():f for f in b.GetFootprints()}
pt=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def tr(n,pts,w=.18,l=p.F_Cu):
 for a,c in zip(pts,pts[1:]):
  t=p.PCB_TRACK(b);t.SetStart(pt(*a));t.SetEnd(pt(*c));t.SetWidth(p.FromMM(w));t.SetLayer(l);t.SetNet(b.FindNet(n));b.Add(t)
def via(n,x,y):
 v=p.PCB_VIA(b);v.SetPosition(pt(x,y));v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(n));b.Add(v)
# Consolidate overlapping same-net vias and reconnect their attached tracks.
vs=[t for t in b.GetTracks() if isinstance(t,p.PCB_VIA)]
removed=set()
for i,a in enumerate(vs):
 if i in removed:continue
 for j,c in enumerate(vs[i+1:],i+1):
  if j in removed or a.GetNetCode()!=c.GetNetCode():continue
  if (a.GetPosition()-c.GetPosition()).EuclideanNorm()<p.FromMM(.55):
   for t in list(b.GetTracks()):
    if isinstance(t,p.PCB_VIA):continue
    if t.GetNetCode()==c.GetNetCode():
     if t.GetStart()==c.GetPosition():t.SetStart(a.GetPosition())
     if t.GetEnd()==c.GetPosition():t.SetEnd(a.GetPosition())
   b.RemoveNative(c);removed.add(j)
# Shift the analog bus away from timer output/reset pads.
for t in b.GetTracks():
 if t.GetNetname()=='/OSC_RC':
  for getter,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
   q=getter()
   if abs(p.ToMM(q.x)-106.3)<.001:setter(pt(106.05,p.ToMM(q.y)))
# Remove an unused old via; the corresponding signal is already routed on front.
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString()=='58cdd251-bfd9-4625-bbf1-41128b0f91c4':b.RemoveNative(t)
# Fan out blocked QFN pins before coarse maze routing.
fs['C3'].Move(pt(0,-.5))
tr('/VBAT',[(129,89.8125),(129,89.3),(129.15,89.15),(129.15,88.9)])
via('/VBAT',129.15,88.9)
# VIN escapes left, crossing the neighboring VSTOR routing on the back layer.
tr('/VIN_DC',[(127.3125,91),(126.9,91),(126.15,90.75)])
via('/VIN_DC',126.15,90.75)
# Ground stitching, including the probe return.
for x,y in [(136,129.5),(100,80),(110,90),(134,82),(107,120),(116,127),(100,127),(129,123)]:via('/GND',x,y)
p.SaveBoard(str(path),b)
print('Applied QFN escapes, probe clearance and via consolidation.')
