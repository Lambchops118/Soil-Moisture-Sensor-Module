"""Generate the revision-B schematic from an explicit, reviewable pin/net map."""
from pathlib import Path
import sys, copy, uuid, math, json, xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).parent))
from sexpr import parse,dump,get,many,prop,Atom as A
ROOT=Path(__file__).resolve().parents[1]; HW=ROOT/'hardware'
LIB=Path('C:/Program Files/KiCad/10.0/share/kicad/symbols')
uid=lambda: str(uuid.uuid4())
def expr(s): return parse(s)
cache={}
def symbol(lib,name):
    if lib not in cache: cache[lib]=parse((LIB/(lib+'.kicad_sym')).read_text(encoding='utf-8'))
    raw=copy.deepcopy(next(s for s in many(cache[lib],'symbol') if s[1]==name))
    parent=get(raw,'extends')
    if parent:
        base=symbol(lib,parent[1]); old=base[1]; base[1]=name
        for child in many(base,'symbol'): child[1]=child[1].replace(old+'_',name+'_',1)
        for p in many(raw,'property'):
            previous=next((q for q in many(base,'property') if q[1]==p[1]),None)
            if previous: base.remove(previous)
            base.append(p)
        raw=base
    return raw
old=ET.parse(ROOT/'review/net.xml').getroot()
components={c.attrib['ref']:{'value':c.findtext('value'),'footprint':c.findtext('footprint'),'lib':c.find('libsource').attrib['lib'],'part':c.find('libsource').attrib['part'],'nets':{}} for c in old.find('components')}
for net in old.find('nets'):
    n=net.attrib['name'].lstrip('/')
    for node in net:
        components[node.attrib['ref']]['nets'][node.attrib['pin']]=None if n.startswith('unconnected-') else n
def add(ref,lib,part,value,foot,nets): components[ref]=dict(lib=lib,part=part,value=value,footprint=foot,nets=nets)
del components['R6']; del components['R7']
components['R1']['value']='4.75M 1%'; components['R2']['value']='8.25M 1%'
components['R11']['nets']['1']='+3V3'
components['R12']['value']='10k'; components['R13']['value']='47k'; components['RV1']['value']='100k trim'
components['U1']['nets'].update({'6':'GND','12':'GND','14':None,'16':None})
components['L2'].update(value='2.2uH / Isat >= 1.5A',footprint='Inductor_SMD:L_Coilcraft_LPS4018',nets={'1':'BUCK_SW','2':'+3V3'})
components['L1'].update(value='22uH / Isat >= 0.4A',footprint='Inductor_SMD:L_Coilcraft_LPS4018')
components['SC1'].update(value='3F 5.4V PHV-5R4V305-R',footprint='SoilProbe:CP_Eaton_PHV_3F_Vertical_P11.8mm')
components['C6']['value']='10uF 10V X7R'
components['C7']['value']='10uF 10V X7R'
components['C11']['value']='10nF'
for r in ['C1','C2']: components[r]['value']='4.7uF 10V X7R'
for r in ['C3','C5','C8','C9']: components[r]['value']='100nF 10V'
components['C4']['value']='10nF C0G 5%'
cap='Capacitor_SMD:C_0805_2012Metric'; res='Resistor_SMD:R_0805_2012Metric'
add('C10','Device','C','100nF 10V',cap,{'1':'VCC_SENSOR','2':'GND'})
add('C12','Device','C','10uF 10V X7R',cap,{'1':'VBAT','2':'GND'})
add('R14','Device','R','10k',res,{'1':'+3V3','2':'GPIO8_BOOT'})
add('R15','Device','R','10k',res,{'1':'+3V3','2':'GPIO2_BOOT'})
add('R16','Device','R','52.3k 1%',res,{'1':'BUCK_VSET','2':'GND'})
components['U2']['nets'].update({'7':'GPIO8_BOOT','16':'GPIO2_BOOT'})
add('J4','Connector_Generic','Conn_01x02','PCB capacitive probe','SoilProbe:SoilProbe_IDC_40x30mm',{'1':'OSC_RC','2':'GND'})
add('U4','custom','TPS62842DGR','TPS62842DGRR','Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm',{'1':'+3V3','2':'BUCK_SW','3':'GND','4':'BUCK_VSET','5':'BAT_OK','6':'VBAT','7':None,'8':'GND','9':'GND'})
def custom_buck():
    s=expr('(symbol "TPS62842DGR" (pin_names (offset 0.508)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 13.97 0) (effects (font (size 1.27 1.27)))) (property "Value" "TPS62842DGR" (at 0 11.43 0) (effects (font (size 1.27 1.27)))) (property "Footprint" "Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes))) (symbol "TPS62842DGR_0_1" (rectangle (start -10.16 10.16) (end 10.16 -10.16) (stroke (width 0.254) (type default)) (fill (type background)))))')
    unit=[A('symbol'),'TPS62842DGR_1_1']
    for num,name,x,y,a,typ in [(6,'VIN',-15.24,7.62,0,'power_in'),(5,'EN',-15.24,2.54,0,'input'),(3,'MODE',-15.24,-2.54,0,'input'),(8,'GND',-5.08,-15.24,90,'power_in'),(9,'EP',0,-15.24,90,'power_in'),(7,'NC',5.08,-15.24,90,'no_connect'),(2,'SW',15.24,7.62,180,'output'),(1,'VOS',15.24,2.54,180,'input'),(4,'VSET',15.24,-5.08,180,'input')]:
        unit.append(expr(f'(pin {typ} line (at {x} {y} {a}) (length 5.08) (name "{name}" (effects (font (size 1.016 1.016)))) (number "{num}" (effects (font (size 1.016 1.016)))))'))
    s.append(unit); return s
symbols={}
for c in components.values():
    if c['part'] not in symbols: symbols[c['part']]=custom_buck() if c['lib']=='custom' else symbol(c['lib'],c['part'])
symbols['PWR_FLAG']=symbol('power','PWR_FLAG')
library=[A('kicad_symbol_lib'),[A('version'),A('20241209')],[A('generator'),'kicad_symbol_editor']]+list(symbols.values())
(HW/'MoistureRevB.kicad_sym').write_text(dump(library)+'\n',encoding='utf-8')
(HW/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "MoistureRevB")(type "KiCad")(uri "${KIPRJMOD}/MoistureRevB.kicad_sym")(options "")(descr "Pinned revision B symbols")))\n')
(HW/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "SoilProbe")(type "KiCad")(uri "${KIPRJMOD}/SoilProbe.pretty")(options "")(descr "Covered probe and Eaton storage footprint")))\n')
rootuid='79d9ef7d-7411-4059-b8f4-932a051f5864'
sch=expr(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{rootuid}") (paper "A2") (title_block (title "Soil moisture sensor - solar / supercapacitor") (rev "B") (company "BUTLER") (comment 1 "3.3 V / 750 mA buck; storage OV 4.97 V; enable 4.06 V / disable 3.63 V")))')
embedded=[A('lib_symbols')]
for name,s in symbols.items():
    t=copy.deepcopy(s);t[1]='MoistureRevB:'+name;embedded.append(t)
sch.append(embedded)
def note(txt,x,y,size=1.5):
    sch.append(expr(f'(text {json.dumps(txt)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left top)) (uuid "{uid()}"))'))
def wire(x,y,xx,yy): sch.append(expr(f'(wire (pts (xy {x:.4f} {y:.4f}) (xy {xx:.4f} {yy:.4f})) (stroke (width 0) (type default)) (uuid "{uid()}"))'))
def label(n,x,y,a=0):
    sch.append(expr(f'(label {json.dumps(n)} (at {x:.4f} {y:.4f} {a}) (effects (font (size 1.016 1.016)) (justify left bottom)) (uuid "{uid()}"))'))
pins_by_ref={}; ids={}
def place(ref,x,y):
    c=components[ref]; s=symbols[c['part']]; ident=uid(); ids[ref]=ident
    inst=expr(f'(symbol (lib_id "MoistureRevB:{c["part"]}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{ident}") (instances (project "SoilMoistureSensor" (path "/{rootuid}" (reference "{ref}") (unit 1)))))')
    # References and values are aligned beside passives; above IC bodies.
    passive=c['part'] in ['R','C','C_Polarized','L','R_Potentiometer_Trim']
    yy=y-2.54 if passive else y-23
    xx=x+4 if passive else x
    for key,val,py,hide in [('Reference',ref,yy,False),('Value',c['value'],yy+2.54,False),('Footprint',c['footprint'],y,True)]:
        inst.append(expr(f'(property "{key}" {json.dumps(val)} (at {xx} {py} 0) (effects (font (size 1.016 1.016))'+(' (justify left)' if passive else '')+(' (hide yes)' if hide else '')+'))'))
    sch.append(inst); pins_by_ref[ref]={}
    done=set()
    for unit in many(s,'symbol'):
        for p in many(unit,'pin'):
            num=get(p,'number')[1]; at=get(p,'at'); px=x+float(at[1]); py=y-float(at[2]); a=int(at[3]); n=c['nets'].get(num)
            pins_by_ref[ref][num]=[px,py,n]
            if (px,py) in done: continue
            done.add((px,py))
            if n is None:
                sch.append(expr(f'(no_connect (at {px} {py}) (uuid "{uid()}"))'));continue
            length=5.08; rad=math.radians(a); ex=round(px-length*math.cos(rad),4); ey=round(py+length*math.sin(rad),4)
            wire(px,py,ex,ey)
            label(n,ex,ey,180 if a==0 else (90 if a in [90,270] else 0))
positions={
 'U1':(100.33,78.74),'J1':(38.1,48.26),'L1':(38.1,81.28),'C1':(38.1,116.84),'C2':(88.9,137.16),'C3':(134.62,137.16),'C4':(180.34,137.16),'C5':(226.06,137.16),'SC1':(226.06,78.74),
 'R1':(180.34,48.26),'R2':(180.34,83.82),'R3':(271.78,48.26),'R4':(271.78,83.82),'R5':(271.78,119.38),
 'U2':(406.4,91.44),'C7':(330.2,48.26),'C8':(330.2,83.82),'R8':(330.2,119.38),'C9':(330.2,154.94),'SW1':(388.62,154.94),'SW2':(454.66,154.94),
 'R9':(480.06,48.26),'R14':(480.06,83.82),'R15':(480.06,119.38),'J2':(541.02,73.66),
 'U4':(100.33,233.68),'L2':(177.8,205.74),'R16':(177.8,243.84),'C12':(38.1,233.68),'C6':(226.06,233.68),
 'Q1':(330.2,228.6),'R10':(279.4,228.6),'R11':(279.4,269.24),'U3':(411.48,236.22),'R12':(480.06,205.74),'R13':(480.06,241.3),'RV1':(480.06,281.94),'C10':(353.06,287.02),'C11':(406.4,287.02),'J3':(541.02,231.14),'J4':(541.02,281.94)}
for ref,pos in positions.items(): place(ref,*pos)
for i,n in enumerate(['GND','VIN_DC','VBAT','+3V3','VCC_SENSOR']):
    ref=f'#FLG0{i+1}';components[ref]=dict(part='PWR_FLAG',value='PWR_FLAG',footprint='',nets={'1':n});place(ref,38.1+i*45.72,365.76)
note('01  ENERGY HARVESTING + STORAGE',25.4,20.32,2.54)
note('02  ESP32-C3 + PROGRAMMING',317.5,20.32,2.54)
note('03  3.3 V / 750 mA SUPPLY',25.4,180.34,2.54)
note('04  SWITCHED CAPACITIVE OSCILLATOR',266.7,180.34,2.54)
note('BQ25570 buck disabled. VOUT/LBUCK intentionally open.\nU4 draws from VBAT directly; BAT_OK provides hysteretic shutdown.\nR1/R2: OV = 1.5 x 1.21 x (1 + 8.25/4.75) = 4.967 V.\nR3/R4/R5: OFF 3.635 V; ON 4.056 V.\nJ1: solar source only; Voc <= 5.1 V and power <= 400 mW.\nSC1: Eaton PHV-5R4V305-R, low ESR. Indoor use, <= 65 C.',25.4,290.83)
note('GPIO4 LOW = sensor ON; HIGH = OFF. Retain HIGH in sleep.\nMeasure frequency on GPIO5 after sensor settling; radio off during measurement.\nJ3 is an optional external probe/test connector, parallel with J4.\nJ4 copper is covered by solder mask. Seal probe edges before soil exposure.\nCalibrate dry/wet in the actual soil and coating; frequency is not absolute VWC.\nJ2 pin 1 is 3.3 V OUTPUT/reference, not an external power input.',266.7,320.04)
note('POWER-NET ERC FLAGS (passive storage / switched power)',25.4,350.52)
sch.extend([expr('(sheet_instances (path "/" (page "1")))'),expr('(embedded_fonts no)')])
(HW/'SoilMoistureSensor.kicad_sch').write_text(dump(sch)+'\n',encoding='utf-8')
physical={r:dict(c,uuid=ids[r]) for r,c in components.items() if not r.startswith('#')}
(ROOT/'review/revB/design.json').write_text(json.dumps(physical,indent=2))
print(f'Wrote {len(physical)} components')
