"""Revision B placement and deliberate routing; run using KiCad's Python."""
from pathlib import Path
import json,sys,uuid,xml.etree.ElementTree as ET
import pcbnew as p
ROOT=Path(__file__).resolve().parents[1]; HW=ROOT/'hardware'
MM=p.FromMM
def pt(x,y):return p.VECTOR2I(MM(x),MM(y))
def xy(v):return (p.ToMM(v.x),p.ToMM(v.y))
LIB=Path('C:/Program Files/KiCad/10.0/share/kicad/footprints')
local=HW/'SoilProbe.pretty'
# Mask-covered combs: 0.75 mm fingers / 0.50 mm gaps; no paste or mask openings.
probe=p.FOOTPRINT(None);probe.SetReference('J**');probe.SetValue('Covered capacitive probe')
def pad(fp,n,x,y,w,h,th=False):
    q=p.PAD(fp);q.SetNumber(str(n));q.SetPosition(pt(x,y));q.SetSize(pt(w,h));q.SetShape(p.PAD_SHAPE_RECT if str(n)=='1' or not th else p.PAD_SHAPE_CIRCLE)
    q.SetAttribute(p.PAD_ATTRIB_PTH if th else p.PAD_ATTRIB_SMD)
    if th:q.SetDrillSize(pt(0.9,0.9));q.SetLayerSet(q.PTHMask())
    else:q.SetLayerSet(p.LSET().AddLayer(p.F_Cu))
    fp.Add(q);return q
def line(fp,a,b,layer=p.F_SilkS,width=0.15):
    l=p.PCB_SHAPE(fp);l.SetShape(p.SHAPE_T_SEGMENT);l.SetStart(pt(*a));l.SetEnd(pt(*b));l.SetLayer(layer);l.SetWidth(MM(width));fp.Add(l)
pad(probe,1,-19.5,0,1,30);pad(probe,2,19.5,0,1,30)
for i in range(24):
    # fingers overlap their own bus by 0.5 mm and stop 1 mm short of the other bus
    n=1 if i%2==0 else 2;pad(probe,n,-0.5 if n==1 else 0.5,-14.375+i*1.25,38,0.75)
probe.Reference().SetPosition(pt(0,-16));probe.Reference().SetTextSize(pt(1,1));probe.Value().SetVisible(False)
probe.SetAttributes(p.FP_SMD|p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES)
for a,b in [((-20.25,-15.25),(20.25,-15.25)),((20.25,-15.25),(20.25,15.25)),((20.25,15.25),(-20.25,15.25)),((-20.25,15.25),(-20.25,-15.25))]:line(probe,a,b,p.F_CrtYd,0.05)
probe.SetFPID(p.LIB_ID('SoilProbe','SoilProbe_IDC_40x30mm'));p.FootprintSave(str(local),probe)
sc=p.FOOTPRINT(None);sc.SetReference('SC**');sc.SetValue('PHV-5R4V305-R');sc.SetAttributes(p.FP_THROUGH_HOLE)
pad(sc,1,5.9,0,2.0,2.0,True);pad(sc,2,-5.9,0,2.0,2.0,True)
for layer,x,y,w in [(p.F_SilkS,8.65,4.5,.15),(p.F_Fab,8.65,4.5,.1),(p.F_CrtYd,9.15,5,.05)]:
    for a,b in [((-x,-y),(x,-y)),((x,-y),(x,y)),((x,y),(-x,y)),((-x,y),(-x,-y))]:line(sc,a,b,layer,w)
t=p.PCB_TEXT(sc);t.SetText('+');t.SetPosition(pt(7,1.8));t.SetTextSize(pt(1,1));t.SetLayer(p.F_SilkS);sc.Add(t)
sc.Reference().SetPosition(pt(0,-5.5));sc.Value().SetVisible(False)
sc.SetFPID(p.LIB_ID('SoilProbe','CP_Eaton_PHV_3F_Vertical_P11.8mm'));p.FootprintSave(str(local),sc)
b=p.LoadBoard(str(ROOT/'review/revB/original.kicad_pcb'))
design=json.loads((ROOT/'review/revB/design.json').read_text())
original={f.GetReference():f for f in b.GetFootprints()}
nets={};pinmap={}
for n in ET.parse(ROOT/'review/revB/net.xml').getroot().find('nets'):
    name=n.attrib['name']; ni=p.NETINFO_ITEM(b,name); b.Add(ni);nets[name]=ni
    for v in n:pinmap[(v.attrib['ref'],v.attrib['pin'])]=name
def net(n):return nets[n if n in nets else '/'+n]
for z in list(b.Zones()):b.RemoveNative(z)
# Remove traces for redesigned rails and moved components; preserve established MCU/sensor signals.
drop={'/LBOOST','/LBUCK','/VIN_DC','/VSTOR','/VBAT','/VOUT_SET_N','/BAT_OK','/VCC_SENSOR','/SENSOR_GATE','+3V3','/ESP_RXD','/ESP_TXD','/OSC_RC_DISCH','/RV1_WIPER_TIE'}
for t in list(b.GetTracks()):
    old=t.GetNetname()
    if old in drop:b.RemoveNative(t)
    elif old in nets:
        t.SetNet(nets[old])
        if old in ['/VRDIV','/VBAT_OV_N','/OK_HYST_N','/OK_PROG_N','/VREF_SAMP']:t.Move(pt(0,16))
    else:b.RemoveNative(t)
for ref in ['R6','R7','SC1','L1','L2']:b.RemoveNative(original[ref]);del original[ref]
placements={'SC1':(108.5,101,0),'L1':(124.5,87,0),'L2':(124.5,103.5,180),'U4':(130,108,0),'C1':(124,83,0),'C2':(131.5,86,0),'C6':(123,99.5,0),'C10':(118,74.8,90),'R13':(121.5,75,0),'C12':(134.5,108.325,270),'R14':(104,86.5,0),'R15':(129,61,0),'R16':(126,111.5,0)}
for ref,c in design.items():
    if ref in original:f=original[ref]
    else:
        lib,name=c['footprint'].split(':');f=p.FootprintLoad(str(local if lib=='SoilProbe' else LIB/(lib+'.pretty')),name);assert f,ref;b.Add(f)
    f.SetReference(ref);f.SetValue(c['value']);f.SetFPID(p.LIB_ID(*c['footprint'].split(':')));f.SetPath(p.KIID_PATH('/79d9ef7d-7411-4059-b8f4-932a051f5864/'+c['uuid']))
    if ref in placements:
        x,y,a=placements[ref];f.SetOrientationDegrees(a);f.SetPosition(pt(x,y))
    elif ref in ['U1','R1','R2','R3','R4','R5','C3','C4','C5']:f.Move(pt(0,16))
    if ref=='J4':f.SetPosition(pt(116.5,135));f.SetOrientationDegrees(0);f.SetAttributes(p.FP_SMD)
    for q in f.Pads():
        name=pinmap.get((ref,q.GetNumber()))
        if name:q.SetNet(nets[name])
        if ref=='U4':q.SetLocalClearance(MM(.15))
        # Replace the footprint's 0.2 mm thermal drills with ordinary 0.3 mm drills.
        if ref=='U2' and q.GetAttribute()==p.PAD_ATTRIB_PTH:q.SetDrillSize(pt(.3,.3));q.SetSize(pt(.6,.6))
    f.Value().SetVisible(False);f.Reference().SetTextSize(pt(.7,.7));f.Reference().SetTextThickness(MM(.12))
    original[ref]=f
F=original
def padxy(ref,num):return xy(next(q for q in F[ref].Pads() if q.GetNumber()==str(num)).GetPosition())
def track(n,points,width=.25,layer=p.F_Cu):
    for a,c in zip(points,points[1:]):
        if a==c:continue
        t=p.PCB_TRACK(b);t.SetStart(pt(*a));t.SetEnd(pt(*c));t.SetWidth(MM(width));t.SetLayer(layer);t.SetNet(net(n));b.Add(t)
def via(n,x,y):
    v=p.PCB_VIA(b);v.SetPosition(pt(x,y));v.SetWidth(MM(.6));v.SetDrill(MM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(net(n));b.Add(v)
def connect(n,a,c,mids=(),width=.25,layer=p.F_Cu):track(n,[padxy(*a),*mids,padxy(*c)],width,layer)
# Main buck local power loop. Feedback is routed separately from SW.
connect('BUCK_SW',('U4',2),('L2',1),[(126.7,107.675),(126.7,103.5)],.25)
connect('+3V3',('L2',2),('C6',1),[(123.2,102.5)],.6)
via('+3V3',128.2,106.0);track('+3V3',[padxy('U4',1),(128.2,107.025),(128.2,106.0)],.2)
via('+3V3',121.5,99.5);track('+3V3',[(128.2,106.0),(121.5,106.8),(121.5,99.5)],.4,p.B_Cu)
connect('VBAT',('U4',6),('C12',1),[(133.5,108.325),(133.5,107.375)],.3)
connect('BUCK_VSET',('U4',4),('R16',1),[(127,108.975),(127,110.3),(125.0875,110.3)],.2)
connect('GND',('U4',3),('U4',9),[(128.8,108.325)],.2)
connect('GND',('U4',8),('U4',9),[(131.2,107.025),(131.2,106.2),(130,106.2)],.25)
for x,y in [(130,107.7),(130,108.5),(134.5,110),(125.2,99.5)]:via('GND',x,y)
connect('GND',('C12',2),('U4',9),[(134.5,94),(130,94)],.4,p.B_Cu) if False else None
track('GND',[padxy('C12',2),(134.5,110)],.35)
track('GND',[padxy('C6',2),(125.2,99.5)],.35)
# Storage feeds the new buck directly, bypassing the charger's internal series FET.
track('VBAT',[padxy('SC1',1),(118,101),(118,113),(136,113),(136,107.375),padxy('C12',1)],.8)
# Correct Q1 pull-up and supply all timer power pins.
connect('VCC_SENSOR',('Q1',3),('R12',1),[(108.4375,81.1),(107.5875,81.1)],.3)
connect('VCC_SENSOR',('Q1',3),('U3',4),[(108.86,79)],.3)
connect('VCC_SENSOR',('U3',8),('C10',1),[(116.5,74),(116.5,75.75)],.3)
via('VCC_SENSOR',116.8,73);track('VCC_SENSOR',[padxy('U3',8),(115.7,74),(116.7,73),(116.8,73)],.25)
via('VCC_SENSOR',109.5,78.6);track('VCC_SENSOR',[padxy('Q1',3),(109.5,79),(109.5,78.6)],.25)
track('VCC_SENSOR',[(109.5,78.6),(111,78.6),(111,73),(116.8,73)],.3,p.B_Cu)
connect('SENSOR_GATE',('Q1',1),('R10',2),[(105,78.05),(105,77.5)],.2)
connect('SENSOR_GATE',('Q1',1),('R11',2),[(105,78.05),(105,79.5875)],.2)
# Timing trigger and strapped wiper. Duplicate switch terminals are joined explicitly.
via('OSC_RC',109,75.27);track('OSC_RC',[padxy('U3',2),(109,75.27)],.2)
via('OSC_RC',113.46,81);track('OSC_RC',[(109,75.27),(108.7,75.57),(108.7,81),(113.46,81)],.2,p.B_Cu)
connect('RV1_WIPER_TIE',('RV1',1),('RV1',2),[],.25)
connect('GPIO9_BOOT',('SW2',1),('R9',2),[(99.35,68.5),(105.4125,68.5)],.2) if False else None
# Probe connection stays outside the ground pour once below the soil line.
track('OSC_RC',[padxy('J3',1),(97,79.5),(97,120)],.25)
track('GND',[(136,118),(136,120)],.4);via('GND',136,118)
# Ground pour on both layers, excluded from antenna and sensing regions.
for layer in [p.F_Cu,p.B_Cu]:
    z=p.ZONE(b);z.SetLayer(layer);z.SetNet(net('GND'));z.SetLocalClearance(MM(.2));z.SetPadConnection(p.ZONE_CONNECTION_THERMAL);z.SetThermalReliefGap(MM(.25));z.SetThermalReliefSpokeWidth(MM(.3));z.SetMinThickness(MM(.2))
    poly=z.Outline();poly.NewOutline()
    for x,y in [(95.6,58.7),(137.4,58.7),(137.4,118.5),(95.6,118.5)]:poly.Append(int(MM(x)),int(MM(y)))
    b.Add(z)
# Footprint-reference placement is explicit for tight areas.
refs={'U1':(129,78.3),'R1':(122.5,78),'R2':(125,81.5),'C4':(121.4,75),'R5':(128,81),'R3':(135.8,79.5),'R4':(131.7,83),'U3':(112.5,72.5),'C11':(116.5,80.9),'RV1':(116,85.3),'Q1':(107.5,80.5),'R10':(102.8,76),'R11':(102.4,80.5),'R12':(108.5,83.6),'R13':(119.9,74.5),'U4':(130,89.7),'L2':(123,91),'C6':(122.5,82.9),'C12':(136.2,92.3),'R16':(126,97),'SC1':(109,90),'C10':(117,69.8),'J4':(116.5,103.8),'U2':(116.5,60)}
for r,f in F.items():
    if r in refs and r in ['U1','R1','R2','C4','R5','R3','R4','U4','L2','C6','C12','R16']:refs[r]=(refs[r][0],refs[r][1]+16)
    refs['SC1']=(108.5,95.5);refs['J4']=(116.5,119)
    f.Reference().SetPosition(pt(*(refs[r] if r in refs else (xy(f.GetPosition())[0],xy(f.GetPosition())[1]-2))))
    f.Reference().SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T))
# Functional labels, in dry electronics area.
for txt,x,y,size in [('SOIL MOISTURE / REV B',116.5,49,1),('SOLAR + / -',130,48.2,.7),('3V3 OUT',132.6,56,.6),('RX  TX  GND',131,61,.6),('SOIL LINE - SEAL BELOW',116.5,117,.8)]:
    t=p.PCB_TEXT(b);t.SetText(txt);t.SetPosition(pt(x,y));t.SetTextSize(pt(size,size));t.SetTextThickness(MM(.12));t.SetLayer(p.F_SilkS);b.Add(t)
for shape in b.GetDrawings():
    if shape.GetLayer()==p.Edge_Cuts:shape.SetEnd(pt(138,151.5))
b.BuildConnectivity();p.SaveBoard(str(HW/'SoilMoistureSensor.kicad_pcb'),b)
print('Placed',len(F),'footprints; deliberate routes saved.')








