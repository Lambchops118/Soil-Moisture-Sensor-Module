"""Replace the Coilcraft LPS4018 pair with Changjiang FNR 4x4 parts.

L1 and L2 were the two most expensive passives on the board ($12.77 of parts at a
5-board order) and both are Extended tier with no Basic equivalent. The FNR40xx
series shares one land pattern across every height (datasheet: a=1.9, b=1.1,
C=3.7), so a single footprint covers both, and both replacements have lower DCR
than the parts they replace. Run with KiCad 10's bin/python.exe.
"""
from pathlib import Path
import shutil
import pcbnew as p
from sexpr import parse,dump,many,prop

ROOT=Path(__file__).resolve().parents[1];HW=ROOT/'hardware'
PCB=HW/'SoilMoistureSensor.kicad_pcb';SCH=HW/'SoilMoistureSensor.kicad_sch'
LIB='C:/Program Files/KiCad/10.0/share/kicad/footprints/Inductor_SMD.pretty'
NEW='L_Changjiang_FNR4018S';OLD='L_Coilcraft_LPS4018'

b=p.LoadBoard(str(PCB));fs={f.GetReference():f for f in b.GetFootprints()};added={}
assert fs['L1'].GetFPID().GetLibItemName()==OLD,'Already applied'
backup=ROOT/'review/before-inductor-swap';backup.mkdir(exist_ok=True)
for path in [PCB,SCH,ROOT/'scripts/manufacturing_parts.json']:shutil.copy2(path,backup/path.name)
pt=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))

for ref in ['L1','L2']:
 old=fs[ref];new=p.FootprintLoad(LIB,NEW)
 new.SetParent(b)
 new.SetFPID(p.LIB_ID('Inductor_SMD',NEW))
 new.SetReference(ref);new.SetValue(old.GetValue());new.SetPath(old.GetPath())
 new.SetPosition(old.GetPosition());new.SetOrientation(old.GetOrientation())
 new.SetLayer(old.GetLayer())
 nets={pad.GetNumber():pad.GetNet() for pad in old.Pads()}
 for pad in new.Pads():pad.SetNet(nets[pad.GetNumber()])
 for item,src in [(new.Reference(),old.Reference()),(new.Value(),old.Value())]:
  item.SetPosition(src.GetPosition());item.SetTextAngle(src.GetTextAngle())
  item.SetVisible(src.IsVisible());item.SetLayer(src.GetLayer())
 b.Remove(old);b.Add(new);added[ref]=new
 print(ref,'->',NEW,[(q.GetNumber(),p.ToMM(q.GetPosition()),q.GetNetname()) for q in new.Pads()])

pads={(ref,q.GetNumber()):q.GetPosition() for ref,f in added.items() for q in f.Pads()}
# Re-anchor the stubs that used to land on the old, 0.265mm wider pad centres.
moves={(122.735,87.0):pads[('L1','1')],(126.265,87.0):pads[('L1','2')],
       (126.265,103.5):pads[('L2','1')],(122.735,103.5):pads[('L2','2')]}
for t in b.Tracks():
 if isinstance(t,p.PCB_VIA):continue
 for getter,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
  key=tuple(round(v,3) for v in p.ToMM(getter()))
  if key in moves:setter(moves[key])

# The LBOOST via sat inside L1 pad 2 and the wider pad would bury it further, so
# move it clear of the pad; a via inside an SMD aperture wicks solder off the joint.
for t in list(b.Tracks()):
 if isinstance(t,p.PCB_VIA) and tuple(round(v,3) for v in p.ToMM(t.GetPosition()))==(126.25,87.2):
  t.SetPosition(pt(127.0,87.0))
 elif not isinstance(t,p.PCB_VIA):
  a=tuple(round(v,3) for v in p.ToMM(t.GetStart()));z=tuple(round(v,3) for v in p.ToMM(t.GetEnd()))
  if {a,z}=={(126.25,87.0),(126.25,87.2)}:b.Remove(t)          # old vertical stub into the via
  elif a==(126.25,87.2):t.SetStart(pt(127.0,87.0))             # B.Cu run to U1
  elif z==(126.25,87.2):t.SetEnd(pt(127.0,87.0))
for t in list(b.Tracks()):
 if isinstance(t,p.PCB_VIA):continue
 a=tuple(round(v,3) for v in p.ToMM(t.GetStart()));z=tuple(round(v,3) for v in p.ToMM(t.GetEnd()))
 if {a,z}=={(126.0,87.0),(126.25,87.0)}:b.Remove(t)
track=p.PCB_TRACK(b);track.SetStart(pads[('L1','2')]);track.SetEnd(pt(127.0,87.0))
track.SetWidth(p.FromMM(.25));track.SetLayer(p.F_Cu);track.SetNet(added['L1'].FindPadByNumber('2').GetNet());b.Add(track)

filler=p.ZONE_FILLER(b);filler.Fill(b.Zones());p.SaveBoard(str(PCB),b)
s=parse(SCH.read_text(encoding='utf8'))
for sym in many(s,'symbol'):
 if prop(sym,'Reference')[2] in ('L1','L2'):prop(sym,'Footprint')[2]='Inductor_SMD:'+NEW
for path,text in [(PCB,PCB.read_text(encoding='utf8')),(SCH,dump(s)+'\n')]:
 with open(path,'w',encoding='utf8',newline='') as out:out.write(text.replace('\r\n','\n').replace('\n','\r\n'))
print('Both inductors now use',NEW)
