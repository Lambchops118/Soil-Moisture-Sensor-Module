"""Replace rare E96 megohm values with stocked Basic/Preferred combinations."""
from pathlib import Path
import copy,json,uuid,sys,pcbnew as p
from sexpr import parse,dump,get,many,prop,Atom as A
R=Path(__file__).resolve().parents[1];H=R/'hardware';sp=H/'SoilMoistureSensor.kicad_sch';bp=H/'SoilMoistureSensor.kicad_pcb'
s=parse(sp.read_text(encoding='utf8'));b=p.LoadBoard(str(bp));fs={f.GetReference():f for f in b.GetFootprints()};ss={prop(v,'Reference')[2]:v for v in many(s,'symbol')}
uid=lambda:str(uuid.uuid4());pt=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
template=copy.deepcopy(ss['R1']);foot='Resistor_SMD:R_0603_1608Metric'
# Each tuple: value, pin 1, pin 2, PCB center, schematic center.
parts={
'R1':('2M','VBAT_OV_N','OV_LO_SER',(115,91),(180.34,48.26)),
'R17':('2M','OV_LO_SER','GND',(115,93.5),(226.06,48.26)),
'R2':('2M','VRDIV','OV_HI_SER1',(115,88.5),(180.34,83.82)),
'R18':('2M','OV_HI_SER1','OV_HI_SER2',(111.5,88.5),(180.34,109.22)),
'R19':('3M','OV_HI_SER2','VBAT_OV_N',(108,88.5),(226.06,109.22)),
'R3':('2M','GND','OK_LO_SER',(104.5,93.5),(271.78,48.26)),
'R20':('2M','OK_LO_SER','OK_PROG_N',(108,93.5),(271.78,66.04)),
'R4':('2M','OK_PROG_N','OK_MID_SER1',(108,91),(271.78,83.82)),
'R21':('2M','OK_MID_SER1','OK_MID_SER2',(104.5,91),(271.78,101.6)),
'R22':('2M','OK_MID_SER2','OK_MID_SER3',(101,91),(271.78,119.38)),
'R23':('2M','OK_MID_SER3','OK_HYST_N',(101,93.5),(271.78,137.16)),
'R5':('1.5M','VRDIV','OK_HYST_N',(101,88.5),(271.78,154.94))}
# Remove the five old labeled resistor stubs before moving their symbols.
for ref in ['R1','R2','R3','R4','R5']:
 x,y=map(float,get(ss[ref],'at')[1:3])
 for obj in list(s):
  if not isinstance(obj,list):continue
  if obj[0]=='label':
   a=get(obj,'at')
   if abs(float(a[1])-x)<.01 and abs(abs(float(a[2])-y)-8.89)<.01:s.remove(obj)
  if obj[0]=='wire':
   pts=get(obj,'pts');coords=[tuple(map(float,q[1:3])) for q in pts[1:]]
   if all(abs(xx-x)<.01 and abs(yy-y)<9 for xx,yy in coords):s.remove(obj)
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/VBAT_OV_N','/VRDIV','/OK_PROG_N','/OK_HYST_N']:b.RemoveNative(t)
for ref,(value,n1,n2,pcbpos,schpos) in parts.items():
 sym=ss.get(ref)
 if sym is None:
  sym=copy.deepcopy(template);get(sym,'uuid')[1]=uid();get(get(get(sym,'instances'),'project'),'path')[2][1]=ref
  # reference also appears in the instance annotation.
  for pr in many(get(sym,'instances'),'project'):
   for pa in many(pr,'path'):get(pa,'reference')[1]=ref
  s.append(sym)
 x,y=schpos;get(sym,'at')[1:3]=[A(str(x)),A(str(y))]
 for key,val in [('Reference',ref),('Value',value+' 1%'),('Footprint',foot)]:
  pr=prop(sym,key);pr[2]=val;at=get(pr,'at');at[1:3]=[A(str(x+4)),A(str(y-2.54 if key=='Reference' else y))]
 for net,dy in [(n1,-1),(n2,1)]:
  yy=y+dy*3.81;ey=y+dy*8.89
  s.append(parse(f'(wire (pts (xy {x} {yy}) (xy {x} {ey})) (stroke (width 0) (type default)) (uuid "{uid()}"))'))
  s.append(parse(f'(label "{net}" (at {x} {ey} 90) (effects (font (size 1.016 1.016)) (justify left bottom)) (uuid "{uid()}"))'))
 old=fs.get(ref);oldnets={q.GetNumber():q.GetNet() for q in old.Pads()} if old else {}
 if old:b.RemoveNative(old)
 f=p.FootprintLoad('C:/Program Files/KiCad/10.0/share/kicad/footprints/Resistor_SMD.pretty','R_0603_1608Metric');b.Add(f);f.SetReference(ref);f.SetValue(value+' 1%');f.SetFPID(p.LIB_ID(*foot.split(':')));f.SetPosition(pt(*pcbpos));f.SetPath(p.KIID_PATH('/'+get(s,'uuid')[1]+'/'+get(sym,'uuid')[1]));f.Value().SetVisible(False)
 f.Reference().SetPosition(pt(pcbpos[0],pcbpos[1]-1.1));f.Reference().SetTextSize(pt(.8,.8));f.Reference().SetTextThickness(p.FromMM(.12))
 for q in f.Pads():
  n='/'+(n1 if q.GetNumber()=='1' else n2);ni=b.FindNet(n)
  if ni is None:ni=p.NETINFO_ITEM(b,n);b.Add(ni)
  q.SetNet(ni)
# Correct the explanatory equations and rated hysteresis.
for t in many(s,'text'):
 if 'R1/R2: OV' in t[1]:t[1]='BQ25570 buck disabled; U4 draws from VBAT directly.\nOV: R1+R17 = 4M; R2+R18+R19 = 7M.\nOV = 1.5 x 1.21 x (1 + 7/4) = 4.991 V.\nBAT_OK: bottom 4M, middle 8M, top 1.5M.\nOFF = 3.630 V; ON = 4.084 V. Total divider = 13.5M.\nJ1: solar Voc <= 5.1 V, power <= 400 mW.\nSC1: PHV-5R4V305-R, low ESR, indoor <= 65 C.'
tb=get(s,'title_block');get(tb,'comment')[2]='3.3 V / 750 mA buck; storage OV 4.99 V; enable 4.08 V / disable 3.63 V'
sp.write_text(dump(s)+'\n',encoding='utf8');p.SaveBoard(str(bp),b)
print('Basic 2M x10; Preferred 3M and 1.5M. OV 4.991 V, OFF 3.630 V, ON 4.084 V.')
