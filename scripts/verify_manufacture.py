"""Check exported coordinates, package consistency and release hashes."""
from pathlib import Path
from collections import Counter
import csv, re, json, hashlib, zipfile
r=Path(__file__).resolve().parents[1];m=r/'manufacture'
def coords(path):
 return [(int(x)/1e6,int(y)/1e6,int(d)) for x,y,d in re.findall(r'^X(-?\d+)Y(-?\d+)D0([123])\*',path.read_text(),re.M)]
outline=coords(m/'gerbers/SoilMoistureSensor-Edge_Cuts.gm1')
edges=[];last=None
for x,y,d in outline:
 if d==1:edges.append((last,(x,y)))
 last=(x,y)
degree=Counter(v for e in edges for v in e)
assert len(edges)==13 and all(n==2 for n in degree.values())
assert min(v[0] for v in degree)==0 and max(v[0] for v in degree)==55
assert min(v[1] for v in degree)==0 and max(v[1] for v in degree)==198.5
seen=set();todo=[next(iter(degree))]
while todo:
 v=todo.pop()
 if v in seen:continue
 seen.add(v)
 for a,b in edges:
  if a==v:todo.append(b)
  if b==v:todo.append(a)
assert seen==set(degree),'Multiple outline loops'
for layer in ['F_Cu.gtl','B_Cu.gbl']:
 points=coords(m/'gerbers'/('SoilMoistureSensor-'+layer));assert min(y for x,y,d in points)>24,'Copper reaches structural wedge'
for layer in ['F_Mask.gts','B_Mask.gbs']:
 points=coords(m/'gerbers'/('SoilMoistureSensor-'+layer));assert min(y for x,y,d in points)>113.5,'Mask opening below soil line'
drill=(m/'gerbers/SoilMoistureSensor-NPTH.drl').read_text()
assert 'T1C3.200' in drill
holes={(float(x),float(y)) for x,y in re.findall(r'^X([\d.]+)Y([\d.]+)',drill,re.M)}
assert holes=={(3,165.5),(3,139.5),(52,165.5),(52,139.5)}
with open(m/'bom_jlcpcb.csv',newline='') as f:bom=list(csv.DictReader(f))
with open(m/'cpl_jlcpcb.csv',newline='') as f:cpl=list(csv.DictReader(f))
refs=[ref for row in bom for ref in row['Designator'].split(',')]
assert len(refs)==len(set(refs))==45 and set(refs)=={x['Designator'] for x in cpl}
assert all(re.fullmatch(r'C\d+',row['LCSC Part #']) for row in bom)
assert all(row['Layer']=='top' for row in cpl),'Economic assembly requires all SMT placements on top'
for suffix in ['kicad_pcb','kicad_sch','kicad_pro']:
 name='SoilMoistureSensor.'+suffix;assert (m/'source'/name).read_bytes()==(r/'hardware'/name).read_bytes()
with zipfile.ZipFile(m/'gerbers_jlcpcb.zip') as z:
 assert z.testzip() is None
 for name in z.namelist():assert z.read(name)==(m/'gerbers'/name).read_bytes()
status=json.loads((m/'reports/validation.json').read_text())
status['export_checks']=['Single closed outline: 55 x 198.5mm','No exported copper vertices in structural wedge','No mask flashes below soil line','Four 3.2mm NPTH mounting holes: 49 x 26mm spacing','45 unique matching BOM/CPL designators','All 45 SMT placements on top','Source snapshots and Gerber ZIP match files']
(m/'reports/validation.json').write_text(json.dumps(status,indent=2)+'\n')
hashes={str(p.relative_to(m)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(m.rglob('*')) if p.is_file() and p.name!='sha256.json'}
(m/'sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
print('PASS: outline, copper/mask regions, drills, BOM/CPL, snapshots, ZIP. Hashed',len(hashes),'files.')
