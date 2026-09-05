from pathlib import Path
import pcbnew as p,sys,json
from sexpr import parse,dump,get,many,prop,Atom as A
R=Path(__file__).resolve().parents[1];H=R/'hardware';bp=H/'SoilMoistureSensor.kicad_pcb';sp=H/'SoilMoistureSensor.kicad_sch';b=p.LoadBoard(str(bp));s=parse(sp.read_text(encoding='utf8'));fs={f.GetReference():f for f in b.GetFootprints()};ss={prop(v,'Reference')[2]:v for v in many(s,'symbol')};pt=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def tr(n,pts,w=.2,l=p.F_Cu):
 for a,c in zip(pts,pts[1:]):
  t=p.PCB_TRACK(b);t.SetStart(pt(*a));t.SetEnd(pt(*c));t.SetWidth(p.FromMM(w));t.SetLayer(l);t.SetNet(b.FindNet(n));b.Add(t)
def via(n,x,y):
 v=p.PCB_VIA(b);v.SetPosition(pt(x,y));v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(n));b.Add(v)
# Separate the final divider resistor from the preceding labeled stubs.
for o in s:
 if not isinstance(o,list):continue
 move=False
 if o is ss['R5']:move=True
 elif o[0]=='label':
  at=get(o,'at');move=abs(float(at[1])-271.78)<.001 and ((o[1]=='VRDIV' and abs(float(at[2])-146.05)<.01) or (o[1]=='OK_HYST_N' and abs(float(at[2])-163.83)<.01))
 elif o[0]=='wire':
  ps=get(o,'pts')[1:];move=all(abs(float(q[1])-271.78)<.001 for q in ps) and any(abs(float(q[2])-151.13)<.01 or abs(float(q[2])-158.75)<.01 for q in ps)
 if move:
  if o[0]=='wire':
   for q in get(o,'pts')[1:]:q[2]=A(str(round(float(q[2])+9.06,4)))
  else:
   at=get(o,'at');at[2]=A(str(round(float(at[2])+9.06,4)))
   if o[0]=='symbol':
    for pr in many(o,'property'):
     at=get(pr,'at');at[2]=A(str(round(float(at[2])+9.06,4)))
# Same 0805 Basic capacitor family for input and output bulk capacitors.
for ref in ['C1','C6']:
 old=fs[ref];f=p.FootprintLoad('C:/Program Files/KiCad/10.0/share/kicad/footprints/Capacitor_SMD.pretty','C_0805_2012Metric');b.Add(f);f.SetPosition(old.GetPosition());f.SetOrientationDegrees(old.GetOrientationDegrees());f.SetReference(ref);f.SetPath(old.GetPath());f.SetFPID(p.LIB_ID('Capacitor_SMD','C_0805_2012Metric'));f.Value().SetVisible(False)
 for q in f.Pads():
  oq=next(v for v in old.Pads() if v.GetNumber()==q.GetNumber());q.SetNet(oq.GetNet());a=oq.GetPosition();c=q.GetPosition();tr(q.GetNetname(),[(p.ToMM(a.x),p.ToMM(a.y)),(p.ToMM(c.x),p.ToMM(c.y))],.4)
 f.Reference().SetPosition(old.Reference().GetPosition());b.RemoveNative(old);fs[ref]=f;prop(ss[ref],'Footprint')[2]='Capacitor_SMD:C_0805_2012Metric'
values={**{r:'100nF 50V X7R' for r in ['C3','C5','C8','C9','C10']},**{r:'10uF 25V X5R' for r in ['C6','C7','C12']},'C1':'4.7uF 25V X5R','C2':'4.7uF 25V X5R','C11':'10nF 50V X7R','U3':'TLC555CDR','U2':'ESP32-C3-WROOM-02-N4'}
for ref,value in values.items():prop(ss[ref],'Value')[2]=value;fs[ref].SetValue(value)
# Exposed pad ground and digital-output escape. Vias sit beneath the IC body.
q=next(q for q in fs['U3'].Pads() if q.GetNumber()=='1');q.SetLocalZoneConnection(p.ZONE_CONNECTION_FULL)
tr('/FREQ_IN',[(107.525,124.635),(109,124.635)]);via('/FREQ_IN',109,124.635)
# Project-local ESP footprint records the larger thermal-via drills.
u=fs['U2'];u.SetFPID(p.LIB_ID('SoilProbe','ESP32-C3-WROOM-02_0.3mm_thermal_vias'));old=u.GetPosition();u.SetPosition(pt(0,0));p.FootprintSave(str(H/'SoilProbe.pretty'),u);u.SetPosition(old);prop(ss['U2'],'Footprint')[2]='SoilProbe:ESP32-C3-WROOM-02_0.3mm_thermal_vias'
sp.write_text(dump(s)+'\n',encoding='utf8');p.SaveBoard(str(bp),b)
