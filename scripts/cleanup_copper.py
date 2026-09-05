exec(open('scripts/repair_routes.py').read().split('# Consolidate')[0])
# Clear the old switch fanout where the new Basic footprint needs copper clearance.
ids={'a5eecd57-e2fc-4fd1-adb7-ea1e3a7195d7','e22361f4-64fc-4235-9dcd-bbf38872ee6a','ea484953-f125-4682-985a-6cc9df8d750f','2a5b6d64-7680-4161-a382-03159e5afccb','b76d2b48-ef21-4724-8dba-1cb53cc776d1','940f1ece-1aab-466f-9449-06e73f716938'}
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in ids:b.RemoveNative(t)
tr('/OK_LO_SER',[(105.325,93.5),(107.175,93.5)],.2)
for z in b.Zones():z.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
p.SaveBoard(str(path),b)
