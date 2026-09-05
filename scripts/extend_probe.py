"""Apply the deeper-probe revision to the saved, partially routed rev-B board."""
from pathlib import Path
import pcbnew as p,json,sys
ROOT=Path(__file__).resolve().parents[1];HW=ROOT/'hardware'
sys.path.insert(0,str(ROOT/'scripts'))
from sexpr import parse,dump,get,many,prop,Atom as A
pt=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
b=p.LoadBoard(str(ROOT/'review/revB/pre-extension.kicad_pcb'))
fs={f.GetReference():f for f in b.GetFootprints()}
drop=['/VCC_SENSOR','/OSC_RC','/OSC_RC_DISCH','/RV1_WIPER_TIE','/CTRL_BP','/FREQ_IN']
bad=json.loads((ROOT/'review/revB/drc.json').read_text())
badids={v['items'][0]['uuid'] for v in bad['violations'] if v['type'] in ['items_not_allowed','track_dangling']}
for t in list(b.GetTracks()):
    if t.GetNetname() in drop or t.m_Uuid.AsString() in badids:b.RemoveNative(t)
for ref,(x,y,a) in {'U3':(110,124,0),'R12':(101,121,0),'R13':(117,121,0),'RV1':(116.5,116.5,0),'C10':(115.5,125,90),'C11':(110,128.5,0),'J3':(99,115,0)}.items():
    f=fs[ref];f.SetOrientationDegrees(a);f.SetPosition(pt(x,y));f.Reference().SetPosition(pt(x,y-2))
# Extend the existing covered-copper comb from 30 to 55 mm.
probe=fs['J4'];old=probe.GetPosition()
for q in list(probe.Pads()):probe.RemoveNative(q)
def pad(n,x,y,w,h):
    q=p.PAD(probe);q.SetNumber(str(n));q.SetAttribute(p.PAD_ATTRIB_SMD);q.SetShape(p.PAD_SHAPE_RECT);q.SetSize(pt(w,h));q.SetPosition(pt(116.5+x,162.5+y));q.SetLayerSet(p.LSET().AddLayer(p.F_Cu));q.SetNet(b.FindNet('/OSC_RC' if n==1 else '/GND'));probe.Add(q)
probe.SetPosition(pt(116.5,162.5))
pad(1,-19.5,0,1,55);pad(2,19.5,0,1,55)
for i in range(44):pad(1 if i%2==0 else 2,-.5 if i%2==0 else .5,-26.875+i*1.25,38,.75)
for g in list(probe.GraphicalItems()):
    if isinstance(g,p.PCB_SHAPE):probe.RemoveNative(g)
for a,c in [((-20.25,-27.75),(20.25,-27.75)),((20.25,-27.75),(20.25,27.75)),((20.25,27.75),(-20.25,27.75)),((-20.25,27.75),(-20.25,-27.75))]:
    g=p.PCB_SHAPE(probe);g.SetShape(p.SHAPE_T_SEGMENT);g.SetStart(pt(116.5+a[0],162.5+a[1]));g.SetEnd(pt(116.5+c[0],162.5+c[1]));g.SetLayer(p.F_CrtYd);g.SetWidth(p.FromMM(.05));probe.Add(g)
probe.SetFPID(p.LIB_ID('SoilProbe','SoilProbe_IDC_40x55mm'));probe.Reference().SetPosition(pt(116.5,133.5))
# Save a matching library footprint at the origin.
probe.SetPosition(pt(0,0));p.FootprintSave(str(HW/'SoilProbe.pretty'),probe);probe.SetPosition(pt(116.5,162.5))
for z in b.Zones():
    poly=z.Outline();poly.RemoveAllContours();poly.NewOutline()
    for x,y in [(95.6,58.7),(137.4,58.7),(137.4,131),(95.6,131)]:poly.Append(p.FromMM(x),p.FromMM(y))
for g in b.GetDrawings():
    if g.GetLayer()==p.Edge_Cuts:g.SetEnd(pt(138,191.5))
    if isinstance(g,p.PCB_TEXT) and 'SOIL LINE' in g.GetText():g.SetPosition(pt(116.5,132));g.SetText('MAX SOIL LINE / SEAL BELOW')
# Small QFN ground pins need solid local connections, not starved thermal spokes.
for q in fs['U1'].Pads():
    if q.GetNetname()=='/GND':q.SetLocalZoneConnection(p.ZONE_CONNECTION_FULL)
def track(n,coords,w=.25,layer=p.F_Cu):
    for a,c in zip(coords,coords[1:]):
        t=p.PCB_TRACK(b);t.SetStart(pt(*a));t.SetEnd(pt(*c));t.SetWidth(p.FromMM(w));t.SetLayer(layer);t.SetNet(b.FindNet(n));b.Add(t)
def via(x,y):
    v=p.PCB_VIA(b);v.SetPosition(pt(x,y));v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet('/GND'));b.Add(v)
# Probe bus and local timer nodes: no long analog run back to the ESP32.
track('/OSC_RC',[(107.525,123.365),(106.3,123.365),(106.3,130),(97,130),(97,135)],.25)
track('/GND',[(136,129.5),(136,135)],.4);via(136,129.5)
track('/GND',[(134.45,49.5),(136.8,49.5),(136.8,58.54),(134.5,58.54)],.4,p.B_Cu)
for x,y in [(100,80),(110,90),(134,82),(133,95),(107,120),(116,127),(100,127),(129,123)]:via(x,y)
p.SaveBoard(str(HW/'SoilMoistureSensor.kicad_pcb'),b)
# Preserve symbol UUIDs while updating the assembly policy and probe footprint.
sch=parse((HW/'SoilMoistureSensor.kicad_sch').read_text(encoding='utf-8'))
for s in many(sch,'symbol'):
    ref=prop(s,'Reference')[2]
    if ref=='J4':prop(s,'Footprint')[2]='SoilProbe:SoilProbe_IDC_40x55mm'
    if ref in ['J1','J2','J3','SC1','RV1']:
        get(s,'dnp')[1]=A('yes')
for f in b.GetFootprints():
    if f.GetReference() in ['J1','J2','J3','SC1','RV1']:f.SetDNP(True)
p.SaveBoard(str(HW/'SoilMoistureSensor.kicad_pcb'),b)
(HW/'SoilMoistureSensor.kicad_sch').write_text(dump(sch)+'\n',encoding='utf-8')
print('Board now 43 x 144.5 mm; 55 mm active probe; oscillator beside probe.')


