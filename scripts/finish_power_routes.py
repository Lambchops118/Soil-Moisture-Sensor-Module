exec(open('scripts/repair_routes.py').read().split('# Consolidate')[0])
# Reroute the storage node to give the input pin an unobstructed escape.
for t in list(b.GetTracks()):
 if t.GetNetname()=='/VSTOR':b.RemoveNative(t)
fs['C3'].SetPosition(pt(133.5,89))
# Clean exact duplicate ground vias.
seen=set()
for t in list(b.GetTracks()):
 if isinstance(t,p.PCB_VIA):
  key=(t.GetNetCode(),t.GetPosition().x,t.GetPosition().y)
  if key in seen:b.RemoveNative(t)
  else:seen.add(key)
for t in b.GetTracks():
 if not isinstance(t,p.PCB_VIA) and t.GetWidth()<p.FromMM(.2):t.SetWidth(p.FromMM(.2))
p.SaveBoard(str(path),b)
