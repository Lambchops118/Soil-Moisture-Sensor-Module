"""Scan the JLCPCB catalog for Basic / Preferred-extended alternatives to a part."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from jlc_api import search,slim

def scan(keyword,match=lambda r:True,pages=6,size=100):
 out={}
 for page in range(1,pages+1):
  try:lst=search(keyword,page=page,size=size)
  except Exception:break
  if not lst:break
  for c in lst:
   r=slim(c)
   if r['tier']!='Extended' and match(r):out[r['componentCode']]=r
 return sorted(out.values(),key=lambda r:(r['tier']!='Basic',-(r['stockCount'] or 0)))

def report(title,rows,limit=10):
 print('###',title)
 if not rows:print('   no Basic or Preferred-extended candidate');return
 for r in rows[:limit]:
  print(f"   {r['tier']:<19} {r['componentCode']:<10} {str(r['componentModelEn'])[:28]:<28} {str(r['componentSpecificationEn'])[:12]:<12} stock={str(r['stockCount']):<9} ${r['unitPrice']}  {str(r['describe'])[:80]}")
