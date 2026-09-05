"""Audit every JLCPCB-assembled part for library tier, preferred flag and stock."""
import json,concurrent.futures
from pathlib import Path
from jlc_api import lookup
ROOT=Path(__file__).resolve().parents[1]
rows=json.loads((ROOT/'scripts/manufacturing_parts.json').read_text())
smt=[r for r in rows if r.get('assembly','JLCPCB SMT')=='JLCPCB SMT']
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 audit=list(pool.map(lambda r:{**lookup(r['lcsc']),'refs':r['refs']},smt))
audit.sort(key=lambda a:({'Basic':0,'Preferred extended':1,'Extended':2}.get(a['tier'],3),a['refs']))
(ROOT/'review/jlc-tier-audit.json').write_text(json.dumps({'checked':'2026-09-05','parts':audit},indent=2)+'\n')
width=max(len(a['refs']) for a in audit)
for a in audit:
 print(f"{a['tier']:<19} {a['refs']:<{width}}  {a['componentCode']:<10} {str(a.get('componentModelEn')):<24} stock={a.get('stockCount')}")
counts={}
for a in audit:counts[a['tier']]=counts.get(a['tier'],0)+1
print('\nline items:',counts)
