exec(open('scripts/repair_routes.py').read().split('# Consolidate')[0])
tr('/VBAT_OV_N',[(128.5,93.1875),(128.5,94),(128.2,94.3),(128.2,94.4)],.2);via('/VBAT_OV_N',128.2,94.4)
tr('/VRDIV',[(129,93.1875),(129,94.7),(129.2,94.9),(129.2,95)],.2);via('/VRDIV',129.2,95)
p.SaveBoard(str(path),b)
