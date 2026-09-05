"""Annotate current KiCad sources and export a checked JLCPCB package.

Run with KiCad 10's bin/python.exe from any working directory.
Part selections are in manufacturing_parts.json; this never regenerates routing.
"""
from pathlib import Path
import csv, json, re, subprocess, zipfile, hashlib, shutil
import pcbnew as p
from sexpr import parse,dump,get,many,prop,Atom as A
ROOT=Path(__file__).resolve().parents[1];HW=ROOT/'hardware';OUT=ROOT/'manufacture'
PCB=HW/'SoilMoistureSensor.kicad_pcb';SCH=HW/'SoilMoistureSensor.kicad_sch'
CLI=Path(p.__file__).resolve().parents[0]/'kicad-cli.exe'
if not CLI.exists():CLI=Path('C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
for sub in ['gerbers','stencil','reports','assembly','source']: (OUT/sub).mkdir(parents=True,exist_ok=True)
parts=json.loads((ROOT/'scripts/manufacturing_parts.json').read_text())
byref={ref:row for row in parts for ref in row['refs'].split()}
def write_crlf(path,txt):
 with open(path,'w',encoding='utf8',newline='') as f:f.write(txt.replace('\r\n','\n').replace('\n','\r\n'))
def csvfile(name,headers,rows):
 with open(OUT/name,'w',encoding='utf8',newline='') as f:
  w=csv.writer(f);w.writerow(headers);w.writerows(rows)
def run(*args):
 result=subprocess.run([str(CLI),*map(str,args)],capture_output=True,text=True)
 # KiCad's registry preferences cannot be written in the sandbox; irrelevant to output.
 (OUT/'reports'/('cli-'+args[1]+'-'+args[2]+'.log')).write_text(result.stdout+'\n'+result.stderr,encoding='utf8')
 if result.returncode:raise RuntimeError(result.stdout+result.stderr)
 print(result.stdout.strip())
s=parse(SCH.read_text(encoding='utf8'));b=p.LoadBoard(str(PCB));fs={f.GetReference():f for f in b.GetFootprints()}
symbols={prop(x,'Reference')[2]:x for x in many(s,'symbol') if not prop(x,'Reference')[2].startswith('#')}
assert set(symbols)==set(byref)|{'J4'},'Parts map must cover every purchased component'
for ref,record in byref.items():
 sym=symbols[ref];f=fs[ref];assembly=record.get('assembly','JLCPCB SMT')
 fields={'Manufacturer':record['manufacturer'],'MPN':record['mpn'],'LCSC':record['lcsc'],
         'Assembly':assembly,'Source':record.get('source','https://www.lcsc.com/product-detail/'+record['lcsc']+'.html')}
 for key,value in fields.items():
  old=next((q for q in many(sym,'property') if q[1]==key),None)
  if old:old[2]=value
  else:
   x,y=get(sym,'at')[1:3]
   sym.append(parse(f'(property {json.dumps(key)} {json.dumps(value)} (at {x} {y} 0) (effects (font (size 1.016 1.016)) (hide yes)))'))
  f.SetField(key,value)
  f.GetField(key).SetVisible(False)
 # DNP denotes excluded from automated assembly here; manual fit list is explicit.
 get(sym,'dnp')[1]=A('no' if assembly=='JLCPCB SMT' else 'yes');f.SetDNP(assembly!='JLCPCB SMT')
get(symbols['J4'],'in_bom')[1]=A('no')
fs['J4'].SetAttributes(fs['J4'].GetAttributes()|p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES)
# Shared bottom-left origin gives positive Gerber/drill/CPL coordinates.
b.GetDesignSettings().SetAuxOrigin(p.VECTOR2I(p.FromMM(89),p.FromMM(245.5)))
filler=p.ZONE_FILLER(b);filler.Fill(b.Zones());p.SaveBoard(str(PCB),b)
write_crlf(PCB,PCB.read_text(encoding='utf8'));write_crlf(SCH,dump(s)+'\n')
run('pcb','drc','--schematic-parity','--all-track-errors','--severity-all','--format','json','-o',OUT/'reports/drc.json',PCB)
drc=json.loads((OUT/'reports/drc.json').read_text());assert not drc['violations'] and not drc['unconnected_items'] and not drc['schematic_parity']
run('sch','erc','--severity-all','--format','json','-o',OUT/'reports/erc.json',SCH)
erc=json.loads((OUT/'reports/erc.json').read_text());assert all(not sh['violations'] for sh in erc['sheets'])
run('pcb','export','gerbers','--layers','F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts','--subtract-soldermask','--use-drill-file-origin','-o',OUT/'gerbers',PCB)
run('pcb','export','drill','--format','excellon','--drill-origin','plot','--excellon-separate-th','--generate-report','--report-path',OUT/'reports/drill.txt','-o',OUT/'gerbers',PCB)
run('pcb','export','gerbers','--layers','F.Paste,B.Paste','--use-drill-file-origin','-o',OUT/'stencil',PCB)
run('pcb','export','pos','--format','csv','--units','mm','--side','both','--use-drill-file-origin','-o',OUT/'assembly/kicad_positions.csv',PCB)
run('pcb','export','svg','--layers','F.Fab,F.Silkscreen,Edge.Cuts','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','-o',OUT/'assembly/front.svg',PCB)
run('pcb','export','svg','--layers','B.Fab,B.Silkscreen,Edge.Cuts','--mirror','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','-o',OUT/'assembly/back.svg',PCB)
with open(OUT/'assembly/kicad_positions.csv',newline='',encoding='utf8') as f:positions={row['Ref']:row for row in csv.DictReader(f)}
auto={ref for ref,x in byref.items() if x.get('assembly','JLCPCB SMT')=='JLCPCB SMT'}
assert auto<=set(positions)
bom=[];procurement=[];manual=[]
for row in parts:
 refs=row['refs'].split();f=fs[refs[0]];assembly=row.get('assembly','JLCPCB SMT');source=row.get('source','https://www.lcsc.com/product-detail/'+row['lcsc']+'.html')
 entry=[f.GetValue(),','.join(refs),f.GetFPID().GetLibItemName(),row['lcsc']]
 if assembly=='JLCPCB SMT':
  assert re.fullmatch(r'C\d+',row['lcsc']);bom.append(entry)
 detail=[','.join(refs),len(refs),f.GetValue(),str(f.GetFPID().GetLibItemName()),row['manufacturer'],row['mpn'],row['lcsc'],assembly,source,row.get('note','')]
 procurement.append(detail)
 if assembly!='JLCPCB SMT':manual.append(detail)
solar=['SOL1 (external)',1,'123mW solar module','29x23mm rear solder pads','ANYSOLAR','SM141K04L','C22012449','Hand solder - external carrier','https://item.szlcsc.com/23442921.html','Not on main-board CPL. Hand solder <=5 seconds below 400C; no high-temperature reflow.']
procurement.append(solar);manual.append(solar)
headers=['Designator','Quantity','Value','Footprint','Manufacturer','MPN','LCSC Part #','Assembly','Source URL','Notes']
csvfile('bom_jlcpcb.csv',['Comment','Designator','Footprint','LCSC Part #'],bom)
csvfile('bom_all_parts.csv',headers,procurement);csvfile('manual_parts.csv',headers,manual)
cpl=[]
for ref in sorted(auto,key=lambda v:(re.sub(r'\d','',v),int(re.search(r'\d+',v)[0]))):
 row=positions[ref];x=float(row['PosX']);y=float(row['PosY']);assert 0<=x<=55 and 0<=y<=198.5
 cpl.append([ref,f'{x:.6f}',f'{y:.6f}',row['Side'],row['Rot']])
csvfile('cpl_jlcpcb.csv',['Designator','Mid X','Mid Y','Layer','Rotation'],cpl)
assert {r for x in bom for r in x[1].split(',')}=={x[0] for x in cpl}
assert all(not q.IsOnLayer(p.F_Mask) and not q.IsOnLayer(p.B_Mask) for q in fs['J4'].Pads())
for src in [PCB,SCH,HW/'SoilMoistureSensor.kicad_pro',ROOT/'scripts/manufacturing_parts.json']:shutil.copy2(src,OUT/'source'/src.name)
shutil.copytree(HW/'SoilProbe.pretty',OUT/'source/SoilProbe.pretty',dirs_exist_ok=True)
for name in ['fp-lib-table','sym-lib-table','MoistureRevB.kicad_sym']:shutil.copy2(HW/name,OUT/'source'/name)
with zipfile.ZipFile(OUT/'gerbers_jlcpcb.zip','w',zipfile.ZIP_DEFLATED) as z:
 for path in sorted((OUT/'gerbers').iterdir()):z.write(path,path.name)
assert len(list((OUT/'gerbers').glob('*.drl')))==2
assert len(list((OUT/'gerbers').glob('*.gtl')))==1 and len(list((OUT/'gerbers').glob('*.gbl')))==1
summary={'automated_components':len(auto),'automated_bom_lines':len(bom),'manual_board_components':len(byref)-len(auto),'external_panel':1,'lcsc_missing':['SC1 (user-approved external purchase)'],'origin_mm':[89,245.5],'drc_violations':0,'unconnected_items':0,'schematic_parity_issues':0,'erc_violations':0,'board_thickness_mm':p.ToMM(b.GetDesignSettings().GetBoardThickness()),'size_mm':[55,198.5],'status':'CAD exports verified; supplier stock and assembly orientation approval still required'}
(OUT/'reports/validation.json').write_text(json.dumps(summary,indent=2)+'\n')
hashes={str(path.relative_to(OUT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(OUT.rglob('*')) if path.is_file() and path.name!='sha256.json'}
(OUT/'sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
print(json.dumps(summary,indent=2))
