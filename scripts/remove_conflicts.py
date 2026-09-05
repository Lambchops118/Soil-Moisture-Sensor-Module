from pathlib import Path
import pcbnew as p,json
R=Path(__file__).resolve().parents[1];path=R/'hardware/SoilMoistureSensor.kicad_pcb';b=p.LoadBoard(str(path));d=json.loads((R/'review/revB/drc.json').read_text())
ids={'8fac81bf-ee59-4e8e-92ae-32bdfcd0ec10','5f2d0f1b-387d-40de-be3f-dfb75a63c154','f4bf637d-78a9-4a4e-aa23-e9cd4aa65a7c','d3efe043-c2e0-4bbf-b2cd-ef29eacea80f'}
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in ids:b.RemoveNative(t)
p.SaveBoard(str(path),b)
