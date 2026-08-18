"""Build image.html and audio.html — same table engine as the video atlas,
parameterized per modality via a CONFIG object injected into a generic JS.

Usage: python3 build_media.py [rows_dir]
rows_dir holds image_rows.json / audio_rows.json (default: ../../data).
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from verdicts_media import IMAGE, AUDIO  # noqa: E402

TABS = """<nav class="tabs" aria-label="Atlas sections">
<a href="./"{v}>Video <span class="n">332</span></a>
<a href="image.html"{i}>Image <span class="n">587</span></a>
<a href="audio.html"{a}>Audio <span class="n">126</span></a>
</nav>"""


def tabs(cur):
    m = {'v': '', 'i': '', 'a': ''}
    m[cur] = ' aria-current="page"'
    return TABS.format(**m)


CFG = {
 'image': {
   'title': 'fal.ai Image Model Atlas',
   'h1': 'Every image generation model on fal.ai',
   'dek': 'All <b>587 endpoints</b> across text-to-image and image-to-image — generators, editors, upscalers, and utilities — with pricing normalised to <b>USD per image at 1&nbsp;MP</b> (1024&times;1024). Click any row for its strongest/weakest side and use-cases.',
   'verdicts': IMAGE,
   'types': {'t2i': ['b-t2v', 'T2I', 'Text→Image'], 'i2i': ['b-i2v', 'I2I', 'Image→Image'], 'both': ['b-ref', 'T2I+I2I', 'Text + Image input']},
   'tiers': [0.01, 0.03, 0.08, 0.2],
   'price_head': '$/image @1MP', 'price_dp': 3, 'na': 'compute/token-billed',
   'num_key': 'max_mp', 'num_head': 'Max MP', 'num_suffix': ' MP', 'num_missing': 'n/a',
   'cols': [('size_opts', 'Size options', 'small'), ('aspect', 'Aspect ratios', 'small'),
            ('img_input', 'Image input', 'cap'), ('mask', 'Mask / inpaint', 'cap'),
            ('lora', 'LoRA', 'cap'), ('ref', 'Style / ref', 'cap'), ('batch', 'Batch max', 'num')],
   'facets': [('img_input', 'Image input'), ('mask', 'Mask/inpaint'), ('lora', 'LoRA'), ('ref', 'Style/ref')],
   'ranges': [('usd', '$ / image range', '0.001', 'compute/token-billed rows'),
              ('max_mp', 'Max MP range', '0.1', 'rows without a size cap')],
   'footer': """<p><b>Method.</b> Endpoint list from fal's model index (categories text-to-image + image-to-image, all pages, de-duplicated). Size, aspect, mask, LoRA, reference and batch fields read from each endpoint's published <code>openapi.json</code>. Pricing from fal's pricing copy — model metadata where present, scraped from the model page otherwise.</p>
<p><b>Read $/image as a 1&nbsp;MP rate.</b> fal bills images per image, per megapixel, per mode tier, or per token; everything is normalised to one 1024&times;1024 output (mid tier where modes exist; for editors that bill input + output, one 1&nbsp;MP input is assumed). Larger sizes scale roughly with megapixels. Token-billed models (GPT&nbsp;Image, some Gemini tiers) vary too much with settings for one number — they show as unpriced with the basis in the expanded row.</p>
<p>83 legacy endpoints (SD/SDXL-era) are billed per GPU compute-second and show as compute-billed. <b>Sides and use-cases</b> are researched judgement per family, not benchmarks — shortlist, then test.</p>""",
 },
 'audio': {
   'title': 'fal.ai Audio Model Atlas',
   'h1': 'Every audio generation model on fal.ai',
   'dek': 'All <b>126 endpoints</b> across text-to-speech, music, SFX and audio-to-audio — with pricing normalised to <b>USD per minute of output</b>. Click any row for its strongest/weakest side and use-cases.',
   'verdicts': AUDIO,
   'types': {'tts': ['b-t2v', 'TTS', 'Text→Speech'], 'music': ['b-i2v', 'MUSIC', 'Music generation'],
             'sfx': ['b-ref', 'SFX', 'Sound effects / ambient'], 'a2a': ['b-x4', 'A2A', 'Audio→Audio edit'],
             's2s': ['b-x5', 'S2S', 'Speech→Speech']},
   'tiers': [0.02, 0.06, 0.15, 0.4],
   'price_head': '$/min output', 'price_dp': 3, 'na': 'flat/compute-billed',
   'num_key': 'max_dur', 'num_head': 'Max duration', 'num_suffix': ' s', 'num_missing': 'input/text-driven',
   'cols': [('dur_opts', 'Duration options', 'small'), ('voices', 'Voices', 'small'),
            ('langs', 'Languages', 'small'), ('clone', 'Voice clone', 'cap'),
            ('lyrics', 'Lyrics control', 'cap'), ('audio_in', 'Audio input', 'cap'),
            ('formats', 'Output formats', 'small')],
   'facets': [('clone', 'Voice clone'), ('lyrics', 'Lyrics'), ('audio_in', 'Audio input')],
   'ranges': [('usd', '$ / min range', '0.001', 'flat/compute-billed rows'),
              ('max_dur', 'Duration range (s)', '1', 'text/input-driven rows')],
   'footer': """<p><b>Method.</b> Endpoint list from fal's model index (categories text-to-speech, text-to-audio, audio-to-audio, speech-to-speech; audio-to-text excluded — transcription is not generation). Duration, voice, language and format fields read from each endpoint's published <code>openapi.json</code>; pricing from fal's pricing copy, page-scraped where metadata carries none.</p>
<p><b>Read $/min as a comparison rate.</b> Music/SFX models bill per second or per clip (converted via the endpoint's default clip length); TTS bills per 1,000 characters, converted at ~750 characters ≈ 1 minute of speech — an estimate that varies with speaking rate. Flat-per-clip rows where clip length isn't exposed show unpriced with the basis in the expanded row.</p>
<p><b>Sides and use-cases</b> are researched judgement per family, not benchmarks — shortlist, then test.</p>""",
 },
}


def build_payload(rows, verdicts):
    fams = {}
    for r in rows:
        f = r['family']
        if f not in fams:
            v = verdicts.get(f) or ('', '', '', '')
            fams[f] = list(v)
    keep = ['id', 'family', 'lab', 'type', 'usd', 'basis', 'conf', 'desc',
            'max_mp', 'size_opts', 'aspect', 'img_input', 'mask', 'lora', 'ref', 'batch',
            'max_dur', 'dur_opts', 'voices', 'langs', 'clone', 'lyrics', 'audio_in', 'formats']
    compact = [{k: r[k] for k in keep if k in r} for r in rows]
    return {'rows': compact, 'fams': fams}


def stats_html(rows, name):
    n = len(rows)
    pr = sorted(r['usd'] for r in rows if r.get('usd') is not None)
    fams = len(set(r['family'] for r in rows))
    if name == 'image':
        items = [
            (str(n), 'Endpoints'),
            (f"{sum(1 for r in rows if r['type']=='t2i')} / {sum(1 for r in rows if r['type']!='t2i')}", 'T2I / image-input'),
            (str(fams), 'Model families'),
            (str(sum(1 for r in rows if r.get('mask') == 'Yes')), 'Mask / inpaint'),
            (str(sum(1 for r in rows if r.get('lora') == 'Yes')), 'LoRA support'),
            (str(sum(1 for r in rows if (r.get('max_mp') or 0) >= 16)), '4K-capable'),
            (f"${pr[0]:.4f}–${pr[-1]:.2f}", '$/image range'),
        ]
    else:
        items = [
            (str(n), 'Endpoints'),
            (str(sum(1 for r in rows if r['type'] == 'tts')), 'TTS'),
            (str(sum(1 for r in rows if r['type'] == 'music')), 'Music'),
            (str(sum(1 for r in rows if r['type'] in ('sfx', 'a2a', 's2s'))), 'SFX / A2A / S2S'),
            (str(fams), 'Model families'),
            (str(sum(1 for r in rows if r.get('clone') == 'Yes')), 'Voice cloning'),
            (str(sum(1 for r in rows if r.get('lyrics') == 'Yes')), 'Lyrics control'),
            (f"${pr[0]:.4f}–${pr[-1]:.2f}", '$/min range'),
        ]
    return ''.join(f'<div class="stat"><span class="n">{a}</span><span class="k">{b}</span></div>'
                   for a, b in items)


JS = r"""
const D = __PAYLOAD__;
const C = __CONFIG__;
const rows = D.rows, fams = D.fams;

const esc = s => String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tier = p => { if(p==null) return 0; const t=C.tiers; return p<t[0]?1:p<t[1]?2:p<t[2]?3:p<t[3]?4:5; };
const money = p => p==null ? `<span class="pna">${esc(C.na)}</span>`
  : `<span class="pill p${tier(p)}">$${p.toFixed(p<0.1?C.price_dp:2)}</span>`;
const capCell = v => !v ? '<span class="no">&mdash;</span>'
  : /^Yes/i.test(v) ? '<span class="yes">Yes</span>'
  : /^(Partial|Input)/i.test(v) ? `<span class="part">${esc(v)}</span>` : '<span class="no">No</span>';

const FACETS=[
  {id:'fam', label:'Family', get:r=>[r.family], search:true},
  {id:'type', label:'Type', get:r=>[r.type], name:t=>(C.types[t]||[0,t,t])[2]},
  ...C.facets.map(([k,label])=>({id:k,label,get:r=>[/^Yes/.test(r[k]||'')?'y':'n'],name:t=>t==='y'?'Yes':'No',sort:(a,b)=>a<b?1:-1})),
];
FACETS.forEach(f=>{
  const set=new Set(); rows.forEach(r=>f.get(r).forEach(t=>set.add(t)));
  f.opts=[...set].sort(f.sort||((a,b)=>String(a).localeCompare(String(b))));
});
const RANGES=C.ranges.map(([k,label,step,missing])=>({id:k,label,step,missing,get:r=>r[k]}));

const st={q:'', sel:Object.fromEntries(FACETS.map(f=>[f.id,new Set()])),
  rng:Object.fromEntries(RANGES.map(r=>[r.id,[null,null]])), sort:{key:'fam',dir:1}};
const tb=document.getElementById('tb'), cnt=document.getElementById('count'), bar=document.getElementById('facetbar');
const NCOLS = 4 + C.cols.length;

let openFacet=null;
function closePanels(){ if(openFacet){openFacet.classList.remove('open'); openFacet=null;} }
document.addEventListener('click',e=>{ if(!e.target.closest('.facet')) closePanels(); });
document.addEventListener('keydown',e=>{ if(e.key==='Escape') closePanels(); });
function openToggle(w){ const was=w.classList.contains('open'); closePanels(); if(!was){w.classList.add('open'); openFacet=w;} return !was; }

FACETS.forEach(f=>{
  const w=document.createElement('div'); w.className='facet';
  w.innerHTML=`<button class="fbtn" type="button">${f.label}<span class="bdg" hidden></span><span class="car" aria-hidden="true">▾</span></button>
  <div class="panel" role="group" aria-label="${esc(f.label)} filter">
    ${f.search?'<input class="psearch" type="search" placeholder="Find…">':''}
    <div class="tools"><button type="button" class="all">All</button><button type="button" class="none">None</button></div>
    <div class="opts"></div></div>`;
  const opts=w.querySelector('.opts');
  opts.innerHTML=f.opts.map(t=>`<label class="opt"><input type="checkbox" value="${esc(t)}"><span>${esc(f.name?f.name(t):t)}</span></label>`).join('');
  const badge=()=>{const n=st.sel[f.id].size,b=w.querySelector('.bdg'); b.hidden=!n; b.textContent=n;};
  w.querySelector('.fbtn').addEventListener('click',()=>{ if(openToggle(w)){const s=w.querySelector('.psearch'); if(s)s.focus();} });
  opts.addEventListener('change',e=>{ const v=e.target.value; e.target.checked?st.sel[f.id].add(v):st.sel[f.id].delete(v); badge(); render(); });
  w.querySelector('.all').addEventListener('click',()=>{ f.opts.forEach(t=>st.sel[f.id].add(t)); opts.querySelectorAll('input').forEach(i=>i.checked=true); badge(); render(); });
  w.querySelector('.none').addEventListener('click',()=>{ st.sel[f.id].clear(); opts.querySelectorAll('input').forEach(i=>i.checked=false); badge(); render(); });
  const ps=w.querySelector('.psearch');
  if(ps) ps.addEventListener('input',()=>{ const q=ps.value.toLowerCase();
    opts.querySelectorAll('.opt').forEach(o=>{o.style.display=o.textContent.toLowerCase().includes(q)?'':'none';}); });
  f.reset=()=>{ st.sel[f.id].clear(); opts.querySelectorAll('input').forEach(i=>i.checked=false); badge(); };
  bar.appendChild(w);
});
RANGES.forEach(rg=>{
  const w=document.createElement('div'); w.className='facet';
  w.innerHTML=`<button class="fbtn" type="button">${esc(rg.label)}<span class="bdg" hidden>●</span><span class="car" aria-hidden="true">▾</span></button>
  <div class="panel"><div class="rng">
    <input type="number" class="rmin" placeholder="min" step="${rg.step}" min="0" aria-label="${esc(rg.label)} minimum"><span aria-hidden="true">–</span>
    <input type="number" class="rmax" placeholder="max" step="${rg.step}" min="0" aria-label="${esc(rg.label)} maximum">
    <button type="button" class="clr">Clear</button></div>
  <p class="rnote">While a range is set, ${esc(rg.missing)} are hidden.</p></div>`;
  const rmin=w.querySelector('.rmin'), rmax=w.querySelector('.rmax'), bdg=w.querySelector('.bdg');
  const upd=()=>{ st.rng[rg.id]=[rmin.value===''?null:+rmin.value, rmax.value===''?null:+rmax.value];
    bdg.hidden=st.rng[rg.id][0]==null&&st.rng[rg.id][1]==null; render(); };
  w.querySelector('.fbtn').addEventListener('click',()=>{ if(openToggle(w)) rmin.focus(); });
  rmin.addEventListener('input',upd); rmax.addEventListener('input',upd);
  w.querySelector('.clr').addEventListener('click',()=>{rmin.value='';rmax.value='';upd();});
  rg.reset=()=>{rmin.value='';rmax.value='';st.rng[rg.id]=[null,null];bdg.hidden=true;};
  bar.appendChild(w);
});

function match(r){
  for(const f of FACETS){ const sel=st.sel[f.id]; if(sel.size && !f.get(r).some(t=>sel.has(t))) return false; }
  for(const rg of RANGES){
    const [lo,hi]=st.rng[rg.id];
    if(lo==null&&hi==null) continue;
    const v=rg.get(r);
    if(v==null) return false;
    if(lo!=null&&v<lo) return false;
    if(hi!=null&&v>hi) return false;
  }
  if(st.q){ const h=(r.id+' '+r.family+' '+(r.lab||'')+' '+(r.desc||'')).toLowerCase();
    if(!st.q.split(/\s+/).every(t=>h.includes(t))) return false; }
  return true;
}
const TORD=Object.fromEntries(Object.keys(C.types).map((k,i)=>[k,i]));
function sortList(list){
  const {key,dir}=st.sort;
  const nullLast=pick=>(a,b)=>{ const va=pick(a),vb=pick(b);
    if(va==null&&vb==null) return a.id.localeCompare(b.id);
    if(va==null) return 1; if(vb==null) return -1;
    return (va-vb)*dir||a.id.localeCompare(b.id); };
  const cmp={ fam:(a,b)=>a.family.localeCompare(b.family)*dir||a.id.localeCompare(b.id),
    type:(a,b)=>(TORD[a.type]-TORD[b.type])*dir||a.id.localeCompare(b.id),
    price:nullLast(r=>r.usd), num:nullLast(r=>r[C.num_key]) }[key];
  list.sort(cmp);
}
document.querySelectorAll('th[data-sort]').forEach(th=>{
  th.addEventListener('click',()=>{
    const k=th.dataset.sort;
    if(st.sort.key===k) st.sort.dir*=-1; else st.sort={key:k,dir:1};
    document.querySelectorAll('th[data-sort]').forEach(o=>o.removeAttribute('aria-sort'));
    th.setAttribute('aria-sort', st.sort.dir===1?'ascending':'descending');
    render();
  });
});

function cell(r,[k,_,kind]){
  const v=r[k];
  if(kind==='cap') return `<td class="cap">${capCell(v)}</td>`;
  if(kind==='num') return `<td class="num">${v==null?'<span class="dim">—</span>':esc(v)}</td>`;
  return `<td class="small">${esc(v==null?'—':v)}</td>`;
}
function render(){
  const list=rows.filter(match);
  sortList(list);
  cnt.textContent=`${list.length} of ${rows.length} endpoints`;
  if(!list.length){ tb.innerHTML=`<tr><td colspan="${NCOLS}"><div class="empty">No model matches those filters.</div></td></tr>`; tb.__list=[]; return; }
  const grouped=st.sort.key==='fam';
  let html='', last=null;
  list.forEach((r,ix)=>{
    if(grouped&&r.family!==last){ last=r.family;
      html+=`<tr class="grp"><td colspan="${NCOLS}"><span class="gname">${esc(r.family)}</span><span class="glab">${esc(r.lab||'')}</span></td></tr>`; }
    const seg=r.id.split('/'), tail=seg.pop(), pre=seg.join('/')+'/';
    const t=C.types[r.type]||['b-t2v',r.type,r.type];
    const nv=r[C.num_key];
    html+=`<tr class="row" data-k="${ix}" tabindex="0" role="button" aria-expanded="false">
      <td><span class="eid"><span class="pre">${esc(pre)}</span>${esc(tail)}</span></td>
      <td><span class="badge ${t[0]}">${t[1]}</span></td>
      <td class="price">${money(r.usd)}</td>
      <td class="num">${nv==null?`<span class="dim">${esc(C.num_missing)}</span>`:esc(nv)+esc(C.num_suffix)}</td>
      ${C.cols.map(c=>cell(r,c)).join('')}
    </tr>`;
  });
  tb.innerHTML=html; tb.__list=list;
}
function toggle(tr){
  const nx=tr.nextElementSibling;
  if(nx&&nx.classList.contains('detail')){ nx.remove(); tr.setAttribute('aria-expanded','false'); return; }
  tb.querySelectorAll('tr.detail').forEach(d=>d.remove());
  tb.querySelectorAll('tr.row[aria-expanded="true"]').forEach(d=>d.setAttribute('aria-expanded','false'));
  const r=tb.__list[+tr.dataset.k], v=fams[r.family]||['','','',''];
  const d=document.createElement('tr'); d.className='detail';
  d.innerHTML=`<td colspan="${NCOLS}"><div class="det">
    <div class="s"><h4>Strongest side</h4><p>${esc(v[0]||'—')}</p></div>
    <div class="w"><h4>Weakest side</h4><p>${esc(v[1]||'—')}</p></div>
    <div class="us"><h4>Strongest use-cases</h4><p>${esc(v[2]||'—')}</p></div>
    <div class="uw"><h4>Weakest use-cases</h4><p>${esc(v[3]||'—')}</p></div>
    <div class="meta"><span>${esc(r.basis||'no published rate')}</span>
      <a href="https://fal.ai/models/${r.id}" target="_blank" rel="noopener">open on fal.ai &nearr;</a></div></div></td>`;
  tr.after(d); tr.setAttribute('aria-expanded','true');
}
tb.addEventListener('click',e=>{const tr=e.target.closest('tr.row'); if(tr) toggle(tr);});
tb.addEventListener('keydown',e=>{ if(e.key!=='Enter'&&e.key!==' ')return;
  const tr=e.target.closest('tr.row'); if(tr){e.preventDefault(); toggle(tr);} });

let deb;
document.getElementById('q').addEventListener('input',e=>{
  clearTimeout(deb); const v=e.target.value.trim().toLowerCase();
  deb=setTimeout(()=>{st.q=v; render();},110);
});
document.getElementById('reset').addEventListener('click',()=>{
  FACETS.forEach(f=>f.reset()); RANGES.forEach(r=>r.reset());
  st.q=''; document.getElementById('q').value=''; closePanels(); render();
});
render();
"""


def page(name, rows, cfg, tab):
    payload = build_payload(rows, cfg['verdicts'])
    config = {
        'types': cfg['types'], 'tiers': cfg['tiers'], 'price_dp': cfg['price_dp'],
        'na': cfg['na'], 'num_key': cfg['num_key'], 'num_suffix': cfg['num_suffix'],
        'num_missing': cfg['num_missing'],
        'cols': [[k, h, kind] for k, h, kind in cfg['cols']],
        'facets': [[k, l] for k, l in cfg['facets']],
        'ranges': [list(x) for x in cfg['ranges']],
    }
    head = open(os.path.join(ROOT, 'scripts', 'head.html')).read()
    head = head.replace('<title>fal.ai Video Model Atlas</title>', f"<title>{cfg['title']}</title>")
    thead = (f'<th data-sort="fam" aria-sort="ascending">Endpoint &middot; Family</th>'
             f'<th data-sort="type">Type</th>'
             f'<th class="num" data-sort="price">{cfg["price_head"]}</th>'
             f'<th class="num" data-sort="num">{cfg["num_head"]}</th>'
             + ''.join(f'<th>{h}</th>' for _, h, _k in cfg['cols']))
    js = JS.replace('__PAYLOAD__', json.dumps(payload, separators=(',', ':'))) \
           .replace('__CONFIG__', json.dumps(config, separators=(',', ':')))
    body = f"""<header class="top"><div class="wrap"><div class="mast">
  <div class="eyebrow">fal.ai catalogue survey &middot; 18 Aug 2026</div>
  <h1>{cfg['h1']}</h1>
  <p class="dek">{cfg['dek']}</p>
  {tab}
</div>
<div class="stats">{stats_html(rows, name)}</div>
</div></header>
<div class="rail"><div class="wrap">
  <div class="rail-in">
    <label class="search">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5 14 14"/></svg>
      <input id="q" type="search" placeholder="Search model, family or lab&hellip;" aria-label="Search models">
    </label>
    <button class="chip" id="reset" type="button">Reset all</button>
    <span class="count" id="count"></span>
  </div>
  <div class="facetbar" id="facetbar" role="group" aria-label="Column filters"></div>
</div></div>
<div class="wrap"><div class="scroller"><table>
<thead><tr>{thead}</tr></thead>
<tbody id="tb"></tbody>
</table></div></div>
<footer><div class="wrap">{cfg['footer']}</div></footer>
"""
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="theme-color" content="#FAFAFB" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0D0F13" media="(prefers-color-scheme: dark)">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ctext y='13' font-size='13'%3E%F0%9F%8E%AC%3C/text%3E%3C/svg%3E">
{head}</head>
<body>
{body}
<script>
{js}
</script>
</body>
</html>
"""
    out = os.path.join(ROOT, f'{name}.html')
    with open(out, 'w') as f:
        f.write(doc)
    print(f'wrote {name}.html — {os.path.getsize(out)//1024} KB, {len(rows)} rows')


CSV_COLS = {
 'image': [('id', 'Endpoint'), ('family', 'Family'), ('lab', 'Lab'), ('type', 'Type'),
           ('usd', 'USD/image @1MP'), ('basis', 'Price basis'), ('max_mp', 'Max MP'),
           ('size_opts', 'Size options'), ('aspect', 'Aspect ratios'), ('img_input', 'Image input?'),
           ('mask', 'Mask/inpaint?'), ('lora', 'LoRA?'), ('ref', 'Style/ref?'), ('batch', 'Batch max')],
 'audio': [('id', 'Endpoint'), ('family', 'Family'), ('lab', 'Lab'), ('type', 'Type'),
           ('usd', 'USD/min output'), ('basis', 'Price basis'), ('max_dur', 'Max duration s'),
           ('dur_opts', 'Duration options'), ('voices', 'Voices'), ('langs', 'Languages'),
           ('clone', 'Voice clone?'), ('lyrics', 'Lyrics?'), ('audio_in', 'Audio input?'),
           ('formats', 'Output formats')],
}


def main():
    rows_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data')
    for name, tab_key in (('image', 'i'), ('audio', 'a')):
        rows = json.load(open(os.path.join(rows_dir, f'{name}_rows.json')))
        # persist rows + CSV into repo data/
        with open(os.path.join(ROOT, 'data', f'{name}_rows.json'), 'w') as f:
            json.dump(rows, f, indent=1)
        cols = CSV_COLS[name]
        verd = CFG[name]['verdicts']
        with open(os.path.join(ROOT, 'data', f'fal_{name}_models.csv'), 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow([c[1] for c in cols] + ['Strongest side', 'Weakest side',
                                               'Strongest use-cases', 'Weakest use-cases'])
            for r in sorted(rows, key=lambda x: (x['family'], x['id'])):
                v = verd.get(r['family']) or ('', '', '', '')
                w.writerow([r.get(c[0]) for c in cols] + list(v))
        page(name, rows, CFG[name], tabs(tab_key))


if __name__ == '__main__':
    main()
