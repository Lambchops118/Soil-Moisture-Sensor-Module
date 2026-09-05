"""Query JLCPCB's public SMT parts catalog. Read-only; keeps procurement fields only."""
import json,urllib.request,time
URL='https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList'
KEEP=['componentCode','componentModelEn','componentBrandEn','componentSpecificationEn','componentLibraryType',
      'preferredComponentFlag','stockCount','canPresaleNumber','minPurchaseNum','leastPatchNumber','describe','componentTypeEn']

def search(keyword,page=1,size=50,retries=3):
 body={'currentPage':page,'pageSize':size,'keyword':keyword,'componentAttributes':[],'searchSource':'search',
       'firstSortName':'','secondSortName':'','componentLibraryType':None,'stockFlag':None,'stockSort':None,'sortMode':None}
 req=urllib.request.Request(URL,data=json.dumps(body).encode(),
     headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0','Accept':'application/json'})
 for attempt in range(retries):
  try:return json.loads(urllib.request.urlopen(req,timeout=60).read().decode())['data']['componentPageInfo']['list'] or []
  except Exception:
   if attempt==retries-1:raise
   time.sleep(2*(attempt+1))

def slim(c):
 row={k:c.get(k) for k in KEEP}
 row['unitPrice']=min((p['productPrice'] for p in c.get('componentPrices') or []),default=None)
 row['tier']=('Basic' if c.get('componentLibraryType')=='base'
              else 'Preferred extended' if c.get('preferredComponentFlag') else 'Extended')
 return row

def lookup(code):
 for c in search(code):
  if c.get('componentCode')==code:return slim(c)
 return {'componentCode':code,'tier':'NOT FOUND'}
