"""Compact copper/outline inspection image from the saved KiCad board."""
from pathlib import Path
import pcbnew as p
from PIL import Image,ImageDraw
r=Path(__file__).resolve().parents[1];b=p.LoadBoard(str(r/'hardware/SoilMoistureSensor.kicad_pcb'))
im=Image.new('RGB',(1160,1660),'#fafafa');d=ImageDraw.Draw(im)
for layer,off in [(p.F_Cu,0),(p.B_Cu,580)]:
 def xy(v):return (off+30+(p.ToMM(v.x)-88)*8,45+(p.ToMM(v.y)-47)*8)
 for z in b.Zones():
  if not z.IsOnLayer(layer) or z.GetIsRuleArea():continue
  poly=z.GetFilledPolysList(layer)
  for j in range(poly.OutlineCount()):
   chain=poly.COutline(j);d.polygon([xy(chain.CPoint(k)) for k in range(chain.PointCount())],fill='#cedace')
 for t in b.GetTracks():
  if isinstance(t,p.PCB_VIA):
   x,y=xy(t.GetPosition());d.ellipse((x-2,y-2,x+2,y+2),fill='#444444')
  elif t.GetLayer()==layer:d.line([xy(t.GetStart()),xy(t.GetEnd())],fill='#b75426' if layer==p.F_Cu else '#366bac',width=max(1,round(p.ToMM(t.GetWidth())*8)))
 for f in b.GetFootprints():
  for q in f.Pads():
   if q.IsOnLayer(layer):
    box=q.GetBoundingBox();a=xy(box.GetOrigin());c=xy(box.GetEnd());d.rectangle([a,c],fill='#b75426' if layer==p.F_Cu else '#366bac')
   if q.GetDrillSize().x:
    x,y=xy(q.GetPosition());rad=p.ToMM(q.GetDrillSize().x)*4;d.ellipse((x-rad,y-rad,x+rad,y+rad),fill='white',outline='#444')
  if f.GetLayer()==layer or f.GetReference().startswith('H'):d.text(xy(f.GetPosition()),f.GetReference(),fill='#111111')
 for g in b.GetDrawings():
  if g.GetLayer()==p.Edge_Cuts:d.line([xy(g.GetStart()),xy(g.GetEnd())],fill='#111111',width=2)
 d.text((off+30,15),'FRONT' if layer==p.F_Cu else 'BACK (view through board)',fill='#111111')
im.save(r/'review/board-inspection.png')
