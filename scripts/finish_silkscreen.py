"""Place legible reference labels clear of solder lands and other silk."""
from pathlib import Path
import pcbnew as p,math
R=Path(__file__).resolve().parents[1];path=R/'hardware/SoilMoistureSensor.kicad_pcb';b=p.LoadBoard(str(path));pt=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def box(item,margin=0):
 r=item.GetBoundingBox();return (p.ToMM(r.GetX())-margin,p.ToMM(r.GetY())-margin,p.ToMM(r.GetRight())+margin,p.ToMM(r.GetBottom())+margin)
def intersect(a,c):return a[0]<c[2] and a[2]>c[0] and a[1]<c[3] and a[3]>c[1]
occupied=[box(q,.25) for f in b.GetFootprints() for q in f.Pads() if q.IsOnLayer(p.F_Mask)]
for f in b.GetFootprints():
 for g in f.GraphicalItems():
  if g.GetLayer()==p.F_SilkS:occupied.append(box(g,.12))
# Replace vague combined connector labels with individual pin labels.
for t in list(b.GetDrawings()):
 if isinstance(t,p.PCB_TEXT) and any(v in t.GetText() for v in ['SOLAR +','3V3 OUT','RX  TX']):b.RemoveNative(t)
for txt,x,y in [('SOLAR',129,49.5),('+',131,51.5),('-',131,49.5),('3V3',131.5,56),('GND',131.5,58.54),('TX',131.5,61.08),('RX',131.5,63.62)]:
 t=p.PCB_TEXT(b);t.SetText(txt);t.SetPosition(pt(x,y));t.SetTextSize(pt(.8,.8));t.SetTextThickness(p.FromMM(.12));t.SetLayer(p.F_SilkS);b.Add(t)
for t in b.GetDrawings():
 if isinstance(t,p.PCB_TEXT) and t.GetLayer()==p.F_SilkS:
  if p.ToMM(t.GetTextSize().y)<.8:t.SetTextSize(pt(.8,.8))
  if t.GetText().startswith('SOIL MOISTURE'):t.SetPosition(pt(114,49));t.SetTextSize(pt(.9,.9))
  occupied.append(box(t,.15))
for f in sorted(b.GetFootprints(),key=lambda f:(not f.GetReference().startswith('U'),f.GetReference())):
 t=f.Reference();t.SetTextSize(pt(.8,.8));t.SetTextThickness(p.FromMM(.12));t.SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T));x=p.ToMM(f.GetPosition().x);y=p.ToMM(f.GetPosition().y)
 candidates=[(p.ToMM(t.GetPosition().x),p.ToMM(t.GetPosition().y))]
 for radius in [1.3,1.6,2,2.5,3,3.5,4,4.5,5,6]:
  for a in [-90,90,0,180,-45,-135,45,135]:candidates.append((x+radius*math.cos(math.radians(a)),y+radius*math.sin(math.radians(a))))
 for xx,yy in candidates:
  t.SetPosition(pt(xx,yy));bb=box(t,.08)
  if bb[0]<95.5 or bb[2]>137.5 or bb[1]<47.4 or bb[3]>134.9:continue
  if any(intersect(bb,o) for o in occupied):continue
  occupied.append(bb);break
 else:print('Label needs review',f.GetReference())
# Protect the probe from later ground pours, and prohibit backside copper.
for layer in [p.F_Cu,p.B_Cu]:
 z=p.ZONE(b);z.SetLayer(layer);z.SetIsRuleArea(True);z.SetZoneName('Probe: no ground plane' if layer==p.F_Cu else 'Probe: no back copper');z.SetDoNotAllowZoneFills(True);z.SetDoNotAllowTracks(layer==p.B_Cu);z.SetDoNotAllowVias(True);z.SetDoNotAllowPads(layer==p.B_Cu);z.SetDoNotAllowFootprints(False)
 poly=z.Outline();poly.NewOutline()
 for x,y in [(95.3,132),(137.7,132),(137.7,191.2),(95.3,191.2)]:poly.Append(p.FromMM(x),p.FromMM(y))
 b.Add(z)
p.SaveBoard(str(path),b)
