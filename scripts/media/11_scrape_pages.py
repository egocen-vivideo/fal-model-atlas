import json, os, urllib.request, concurrent.futures as cf, collections
need=[]
for name in ('image','audio'):
    cat=json.load(open(f'all_{name}_models.json'))
    for eid, meta in cat.items():
        if not (meta.get('pricingInfoOverride') or '').strip():
            need.append(eid)
def get(eid):
    p=os.path.join('pages2', eid.replace('/','__')+'.html')
    if os.path.exists(p) and os.path.getsize(p)>50000: return eid,'cached'
    try:
        b=urllib.request.urlopen(urllib.request.Request('https://fal.ai/models/'+eid,
            headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}), timeout=90).read()
        open(p,'wb').write(b); return eid,'ok'
    except Exception as e: return eid,'ERR '+str(e)[:40]
res=[]
with cf.ThreadPoolExecutor(10) as ex:
    for r in ex.map(get, need): res.append(r)
print(collections.Counter(s.split()[0] for _,s in res))
errs=[i for i,s in res if s.startswith('ERR')]
print('errors:', len(errs)); print('\n'.join(errs[:20]))
json.dump(errs, open('pages2_errors.json','w'))
