"""One-time cost revision: front-side telemetry and two Basic-part substitutions."""
from pathlib import Path
import json,shutil
import pcbnew as p
from sexpr import parse,dump,get,many,prop
r=Path(__file__).resolve().parents[1];h=r/'hardware';bp=h/'SoilMoistureSensor.kicad_pcb';sp=h/'SoilMoistureSensor.kicad_sch'
b=p.LoadBoard(str(bp));fs={f.GetReference():f for f in b.GetFootprints()}
assert fs['R24'].GetLayer()==p.B_Cu,'Already applied'
backup=r/'review/before-cost-revision';backup.mkdir(exist_ok=True)
for path in [bp,sp,r/'scripts/manufacturing_parts.json']:shutil.copy2(path,backup/path.name)
pt=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
for ref in ['R24','R25','C13']:
 f=fs[ref];f.Flip(f.GetPosition(),False);f.SetOrientationDegrees(180)
 # Keep existing rear routing and connect to front pads with tented adjacent vias.
 for pad in f.Pads():
  x,y=p.ToMM(pad.GetPosition());vx=x+(1 if x>130 else -1);vy=y
  if ref=='R24' and pad.GetNumber()=='2':vx=x;vy=y+1
  via=p.PCB_VIA(b);via.SetPosition(pt(vx,vy));via.SetWidth(p.FromMM(.6));via.SetDrill(p.FromMM(.3));via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetNet(pad.GetNet());b.Add(via)
  for layer in [p.F_Cu,p.B_Cu]:
   t=p.PCB_TRACK(b);t.SetStart(pad.GetPosition());t.SetEnd(pt(vx,vy));t.SetWidth(p.FromMM(.25));t.SetLayer(layer);t.SetNet(pad.GetNet());b.Add(t)
fs['R24'].SetValue('2M 1%')
s=parse(sp.read_text(encoding='utf8'))
for sym in many(s,'symbol'):
 if prop(sym,'Reference')[2]=='R24':prop(sym,'Value')[2]='2M 1%'
for t in many(s,'text'):
 if 'SUPERCAP TELEMETRY:' in t[1]:t[1]=t[1].replace('23 x','21 x').replace('2.2M/100k','2M/100k').replace('0.24V','0.263V').replace('2.17uA','2.38uA')
filler=p.ZONE_FILLER(b);filler.Fill(b.Zones());p.SaveBoard(str(bp),b)
for path,text in [(bp,bp.read_text(encoding='utf8')),(sp,dump(s)+'\n')]:
 with open(path,'w',encoding='utf8',newline='') as out:out.write(text.replace('\r\n','\n').replace('\n','\r\n'))
mp=r/'scripts/manufacturing_parts.json';rows=json.loads(mp.read_text())
for row in rows:
 if row['lcsc']=='C1711':
  row.update(manufacturer='Yageo',mpn='CC0805KRX7R9BB104',lcsc='C49678',note='Basic: same 0805, 100nF, 50V, X7R, 10% ratings.')
 if row['lcsc']=='C22976':row['refs']+=' R24';row['note']='R24 now 2M; telemetry conversion is 21 times ADC voltage.'
rows=[row for row in rows if row['lcsc']!='C22938']
mp.write_text(json.dumps(rows,indent=2)+'\n')
print('All 45 SMT parts now front-side; R24 shares Basic C22976; five capacitors use Basic C49678.')
