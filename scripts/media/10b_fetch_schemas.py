"""Download each image/audio endpoint's queue OpenAPI schema into oas2/.

12_extract_media.py reads size / aspect / mask / LoRA / duration / voice /
language / format fields from these. (Missing from the Aug 2026 commit — the
oas2/ cache was built ad hoc then.) Concurrency is kept at 3 with backoff and a
slow single-thread retry of every miss: fal rate-limits this endpoint and
answers 404 under load (see ../09_unlisted.py).
"""
import concurrent.futures as cf
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('unl', os.path.join(HERE, '..', '09_unlisted.py'))
unl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(unl)
unl.OAS_DIR = 'oas2'
os.makedirs('oas2', exist_ok=True)

ids = []
for name in ('image', 'audio'):
    ids += list(json.load(open(f'all_{name}_models.json')))
with cf.ThreadPoolExecutor(3) as ex:
    res = dict(zip(ids, ex.map(unl.probe_schema, ids)))
miss = [e for e, ok in res.items() if ok is not True]
for e in miss:
    res[e] = unl.probe_schema(e, slow=True)
print(f'schemas: {sum(1 for v in res.values() if v)} / {len(ids)}')
print('no schema:', [e for e, ok in res.items() if not ok])
