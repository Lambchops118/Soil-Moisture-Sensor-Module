from pathlib import Path
import pcbnew as p
from sexpr import parse,dump,get,many,prop,Atom as A
R=Path(__file__).resolve().parents[1];H=R/'hardware';bp=H/'SoilMoistureSensor.kicad_pcb';sp=H/'SoilMoistureSensor.kicad_sch';b=p.LoadBoard(str(bp));s=parse(sp.read_text(encoding='utf8'));ss={prop(v,'Reference')[2]:v for v in many(s,'symbol')};fs={f.GetReference():f for f in b.GetFootprints()}
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in ['f3794377-450e-4f23-98eb-4d28322244dd','65144f08-f23a-4a28-a21c-62fd62d2ca29']:b.RemoveNative(t)
for ref in ['SW1','SW2']:
 old=fs[ref];pos=old.GetPosition();nets={q.GetNumber():q.GetNet() for q in old.Pads()}
 f=p.FootprintLoad('C:/Program Files/KiCad/10.0/share/kicad/footprints/Button_Switch_SMD.pretty','SW_SPST_TS-1088-xR020');b.Add(f);f.SetPosition(pos);f.SetReference(ref);f.SetValue('TS-1088-AR02016');f.SetPath(old.GetPath());f.SetFPID(p.LIB_ID('Button_Switch_SMD','SW_SPST_TS-1088-xR020'));f.Value().SetVisible(False)
 for q in f.Pads():q.SetNet(nets[q.GetNumber()])
 b.RemoveNative(old);prop(ss[ref],'Footprint')[2]='Button_Switch_SMD:SW_SPST_TS-1088-xR020';prop(ss[ref],'Value')[2]='TS-1088-AR02016'
# Snap R5 and its two stubs back to the schematic connection grid.
for o in s:
 if not isinstance(o,list):continue
 move=o is ss['R5']
 if o[0]=='label':
  at=get(o,'at');move=abs(float(at[1])-271.78)<.001 and (abs(float(at[2])-155.11)<.01 or abs(float(at[2])-172.89)<.01)
 if o[0]=='wire':
  ps=get(o,'pts')[1:];move=all(abs(float(q[1])-271.78)<.001 for q in ps) and any(abs(float(q[2])-160.19)<.01 or abs(float(q[2])-167.81)<.01 for q in ps)
 if move:
  targets=get(o,'pts')[1:] if o[0]=='wire' else [get(o,'at')]+([get(pr,'at') for pr in many(o,'property')] if o[0]=='symbol' else [])
  for at in targets:at[2]=A(str(round(float(at[2])-.17,4)))
sp.write_text(dump(s)+'\n',encoding='utf8');p.SaveBoard(str(bp),b)
