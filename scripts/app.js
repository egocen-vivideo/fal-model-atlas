const D = __PAYLOAD__;
const rows = D.rows, fams = D.fams;

const esc = s => String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tier = p => p==null?0 : p<1.5?1 : p<4?2 : p<8?3 : p<15?4 : 5;
const money = p => p==null ? '<span class="pna">compute&#8209;billed</span>'
  : `<span class="pill p${tier(p)}">$${p.toFixed(2)}</span>`;

function capCell(v){
  if(!v) return '<span class="no">&mdash;</span>';
  const s=String(v);
  if(/^No/i.test(s)){
    const q=s.replace(/^No\s*[—\-]?\s*/,'').replace(/^\((.*)\)$/,'$1').trim();
    return `<span class="no">No${q?' <span class="dim">&middot; '+esc(q)+'</span>':''}</span>`;
  }
  if(/^(Partial|Input only)/i.test(s)) return `<span class="part">${esc(s)}</span>`;
  const q=s.replace(/^Yes\s*[—\-]?\s*/,'').trim();
  return `<span class="yes">Yes</span>${q?' <span class="dim">'+esc(q)+'</span>':''}`;
}
const TYPE={t2v:['b-t2v','T2V'],i2v:['b-i2v','I2V'],ref:['b-ref','REF']};
const TYPE_NAME={t2v:'Text→Video',i2v:'Image→Video',ref:'Reference→Video'};

// ---- stats strip ----
const priced = rows.filter(r=>r.p!=null).map(r=>r.p).sort((a,b)=>a-b);
const stats=[
  [String(rows.length),'Endpoints'],
  ['132 / 200','Text&rarr;V / Image&rarr;V'],
  [String(rows.filter(r=>r.c==='ref').length),'Reference&rarr;V'],
  [String(new Set(rows.map(r=>r.f)).size),'Model families'],
  [String(rows.filter(r=>r.auB==='yes').length),'Generate audio'],
  [String(rows.filter(r=>r.lsB==='yes').length),'Do lipsync'],
  [String(rows.filter(r=>r.eB==='y').length),'Take an end frame'],
  [String(rows.filter(r=>r.mB==='native').length),'Multi&#8209;shot'],
  ['$'+priced[0].toFixed(2)+'&ndash;$'+priced[priced.length-1].toFixed(0),'$/min range'],
];
document.getElementById('stats').innerHTML = stats
  .map(([n,k])=>`<div class="stat"><span class="n">${n}</span><span class="k">${k}</span></div>`).join('');

// ---- facet definitions ----
const secOf = t => /^\d+s$/.test(t) ? parseInt(t,10) : null;
const DUR_TAIL=['>30s','auto','input-driven','unspecified'];
function durSort(a,b){
  const sa=secOf(a), sb=secOf(b);
  if(sa!=null&&sb!=null) return sa-sb;
  if(sa!=null) return -1;
  if(sb!=null) return 1;
  return DUR_TAIL.indexOf(a)-DUR_TAIL.indexOf(b);
}
const DUR_NAME = t =>
  t==='input-driven' ? 'Follows input audio / video' :
  t==='>30s' ? 'Over 30 s' :
  t==='auto' ? 'Auto' :
  t==='unspecified' ? 'Not exposed' : t.replace('s',' s');
const Q_ORDER=['360p','480p','512p','540p','580p','720p','768p','1080p','1440p','2k','4k','low','medium','high','maximum','preset','custom','other','fixed'];
const A_ORDER=['auto','21:9','16:9','3:2','4:3','5:4','1:1','4:5','3:4','2:3','9:16','9:21','free','inherits input','fixed'];
const orderBy = list => (a,b) => {
  const ia=list.indexOf(a), ib=list.indexOf(b);
  return (ia<0?99:ia)-(ib<0?99:ib) || String(a).localeCompare(String(b));
};

const FACETS=[
  {id:'fam',  label:'Family',     get:r=>[r.f], search:true},
  {id:'type', label:'Type',       get:r=>[r.c], name:t=>TYPE_NAME[t]},
  {id:'dur',  label:'Duration',   get:r=>r.dt, sort:durSort, name:DUR_NAME, grid:true},
  {id:'qual', label:'Quality',    get:r=>r.qt, sort:orderBy(Q_ORDER)},
  {id:'ar',   label:'Aspect',     get:r=>r.at, sort:orderBy(A_ORDER)},
  {id:'audio',label:'Audio',      get:r=>[r.auB], name:t=>({yes:'Yes — generates audio',input:'Input only — drives lipsync',no:'No'})[t], sort:orderBy(['yes','input','no'])},
  {id:'start',label:'Start frame',get:r=>[r.sB], name:t=>t==='y'?'Yes':'No', sort:orderBy(['y','n'])},
  {id:'end',  label:'End frame',  get:r=>[r.eB], name:t=>t==='y'?'Yes':'No', sort:orderBy(['y','n'])},
  {id:'cuts', label:'>1 cut',     get:r=>[r.mB], name:t=>({native:'Native multi-shot',keyframe:'Keyframe / element chaining',no:'No — single shot'})[t], sort:orderBy(['native','keyframe','no'])},
  {id:'lips', label:'Lipsync',    get:r=>[r.lsB], name:t=>({yes:'Yes — native or dedicated',partial:'Partial',no:'No'})[t], sort:orderBy(['yes','partial','no'])},
];
FACETS.forEach(f=>{
  const set=new Set();
  rows.forEach(r=>f.get(r).forEach(t=>set.add(t)));
  f.opts=[...set].sort(f.sort||((a,b)=>String(a).localeCompare(String(b))));
});

const RANGES=[
  {id:'price', label:'$ / min range', get:r=>r.p,  step:'0.01', missing:'compute-billed rows'},
  {id:'frames',label:'Frames range',  get:r=>r.mf, step:'1',    missing:'follows-input rows'},
];

// ---- state: all constraints combine in one pass ----
const st={
  q:'',
  sel:Object.fromEntries(FACETS.map(f=>[f.id,new Set()])),
  rng:{price:[null,null],frames:[null,null]},
  sort:{key:'fam',dir:1},
};

const tb=document.getElementById('tb'), cnt=document.getElementById('count');
const bar=document.getElementById('facetbar');

// ---- dropdown scaffolding ----
let openFacet=null;
function closePanels(){
  if(openFacet){
    openFacet.classList.remove('open');
    openFacet.querySelector('.fbtn').setAttribute('aria-expanded','false');
    openFacet=null;
  }
}
document.addEventListener('click',e=>{ if(!e.target.closest('.facet')) closePanels(); });
document.addEventListener('keydown',e=>{ if(e.key==='Escape') closePanels(); });
function openToggle(w){
  const was=w.classList.contains('open');
  closePanels();
  if(!was){
    w.classList.add('open');
    w.querySelector('.fbtn').setAttribute('aria-expanded','true');
    openFacet=w;
  }
  return !was;
}

function mkFacet(f){
  const w=document.createElement('div');
  w.className='facet';
  w.innerHTML=`<button class="fbtn" type="button" aria-expanded="false" aria-haspopup="true">${f.label}<span class="bdg" hidden></span><span class="car" aria-hidden="true">▾</span></button>
  <div class="panel" role="group" aria-label="${esc(f.label)} filter">
    ${f.search?'<input class="psearch" type="search" placeholder="Find…" aria-label="Find option">':''}
    <div class="tools"><button type="button" class="all">All</button><button type="button" class="none">None</button></div>
    <div class="opts${f.grid?' grid':''}"></div>
  </div>`;
  const opts=w.querySelector('.opts');
  opts.innerHTML=f.opts.map(t=>
    `<label class="opt"><input type="checkbox" value="${esc(t)}"><span>${esc(f.name?f.name(t):t)}</span></label>`).join('');
  const badge=()=>{
    const n=st.sel[f.id].size, b=w.querySelector('.bdg');
    b.hidden=!n; b.textContent=n;
  };
  w.querySelector('.fbtn').addEventListener('click',()=>{
    if(openToggle(w)){ const s=w.querySelector('.psearch'); if(s) s.focus(); }
  });
  opts.addEventListener('change',e=>{
    const v=e.target.value;
    e.target.checked ? st.sel[f.id].add(v) : st.sel[f.id].delete(v);
    badge(); render();
  });
  w.querySelector('.all').addEventListener('click',()=>{
    f.opts.forEach(t=>st.sel[f.id].add(t));
    opts.querySelectorAll('input').forEach(i=>i.checked=true);
    badge(); render();
  });
  w.querySelector('.none').addEventListener('click',()=>{
    st.sel[f.id].clear();
    opts.querySelectorAll('input').forEach(i=>i.checked=false);
    badge(); render();
  });
  const ps=w.querySelector('.psearch');
  if(ps) ps.addEventListener('input',()=>{
    const q=ps.value.toLowerCase();
    opts.querySelectorAll('.opt').forEach(o=>{
      o.style.display=o.textContent.toLowerCase().includes(q)?'':'none';
    });
  });
  f.reset=()=>{ st.sel[f.id].clear(); opts.querySelectorAll('input').forEach(i=>i.checked=false); badge(); };
  bar.appendChild(w);
}
FACETS.forEach(mkFacet);

function mkRange(rg){
  const w=document.createElement('div');
  w.className='facet';
  w.innerHTML=`<button class="fbtn" type="button" aria-expanded="false" aria-haspopup="true">${rg.label}<span class="bdg" hidden>●</span><span class="car" aria-hidden="true">▾</span></button>
  <div class="panel" role="group" aria-label="${esc(rg.label)}">
    <div class="rng">
      <input type="number" class="rmin" placeholder="min" step="${rg.step}" min="0" aria-label="${esc(rg.label)} minimum">
      <span aria-hidden="true">–</span>
      <input type="number" class="rmax" placeholder="max" step="${rg.step}" min="0" aria-label="${esc(rg.label)} maximum">
      <button type="button" class="clr">Clear</button>
    </div>
    <p class="rnote">While a range is set, ${rg.missing} are hidden.</p>
  </div>`;
  const rmin=w.querySelector('.rmin'), rmax=w.querySelector('.rmax'), bdg=w.querySelector('.bdg');
  const upd=()=>{
    st.rng[rg.id]=[rmin.value===''?null:+rmin.value, rmax.value===''?null:+rmax.value];
    bdg.hidden=st.rng[rg.id][0]==null && st.rng[rg.id][1]==null;
    render();
  };
  w.querySelector('.fbtn').addEventListener('click',()=>{ if(openToggle(w)) rmin.focus(); });
  rmin.addEventListener('input',upd);
  rmax.addEventListener('input',upd);
  w.querySelector('.clr').addEventListener('click',()=>{ rmin.value=''; rmax.value=''; upd(); });
  rg.reset=()=>{ rmin.value=''; rmax.value=''; st.rng[rg.id]=[null,null]; bdg.hidden=true; };
  bar.appendChild(w);
}
RANGES.forEach(mkRange);

// ---- matching: facets AND ranges AND search, OR within a facet ----
function match(r){
  for(const f of FACETS){
    const sel=st.sel[f.id];
    if(sel.size && !f.get(r).some(t=>sel.has(t))) return false;
  }
  for(const rg of RANGES){
    const [lo,hi]=st.rng[rg.id];
    if(lo==null && hi==null) continue;
    const v=rg.get(r);
    if(v==null) return false;
    if(lo!=null && v<lo) return false;
    if(hi!=null && v>hi) return false;
  }
  if(st.q){
    const h=(r.i+' '+r.f+' '+r.l+' '+r.ds).toLowerCase();
    if(!st.q.split(/\s+/).every(t=>h.includes(t))) return false;
  }
  return true;
}

// ---- sorting via column headers ----
const TORD={t2v:0,i2v:1,ref:2};
function sortList(list){
  const {key,dir}=st.sort;
  const nullLast=(pick)=>(a,b)=>{
    const va=pick(a), vb=pick(b);
    if(va==null&&vb==null) return a.i.localeCompare(b.i);
    if(va==null) return 1;
    if(vb==null) return -1;
    return (va-vb)*dir || a.i.localeCompare(b.i);
  };
  const cmp={
    fam:(a,b)=>a.f.localeCompare(b.f)*dir || a.i.localeCompare(b.i),
    type:(a,b)=>(TORD[a.c]-TORD[b.c])*dir || a.i.localeCompare(b.i),
    price:nullLast(r=>r.p),
    frames:nullLast(r=>r.mf),
  }[key];
  list.sort(cmp);
}
document.querySelectorAll('th[data-sort]').forEach(th=>{
  th.addEventListener('click',()=>{
    const k=th.dataset.sort;
    if(st.sort.key===k) st.sort.dir*=-1;
    else st.sort={key:k,dir:1};
    document.querySelectorAll('th[data-sort]').forEach(o=>o.removeAttribute('aria-sort'));
    th.setAttribute('aria-sort', st.sort.dir===1?'ascending':'descending');
    render();
  });
});

// ---- render ----
function render(){
  const list=rows.filter(match);
  sortList(list);
  cnt.textContent=`${list.length} of ${rows.length} endpoints`;
  if(!list.length){
    tb.innerHTML='<tr><td colspan="12"><div class="empty">No model matches those filters.</div></td></tr>';
    tb.__list=[];
    return;
  }
  const grouped = st.sort.key==='fam';
  let html='', last=null;
  list.forEach((r,ix)=>{
    if(grouped && r.f!==last){
      last=r.f;
      html+=`<tr class="grp"><td colspan="12"><span class="gname">${esc(r.f)}</span><span class="glab">${esc(r.l)}</span></td></tr>`;
    }
    const seg=r.i.split('/'), tail=seg.pop(), pre=seg.join('/')+'/';
    const [cls,lbl]=TYPE[r.c];
    html+=`<tr class="row" data-k="${ix}" tabindex="0" role="button" aria-expanded="false">
      <td><span class="eid"><span class="pre">${esc(pre)}</span>${esc(tail)}</span></td>
      <td><span class="badge ${cls}">${lbl}</span></td>
      <td class="price">${money(r.p)}</td>
      <td class="num">${r.mf?r.mf.toLocaleString():'<span class="dim">follows input</span>'}</td>
      <td class="small">${esc(r.d)}</td>
      <td class="small">${esc(r.q)}</td>
      <td class="small">${esc(r.a)}</td>
      <td class="cap">${capCell(r.au)}</td>
      <td class="cap">${capCell(r.s)}</td>
      <td class="cap">${capCell(r.e)}</td>
      <td class="cap">${capCell(r.m)}</td>
      <td class="cap">${capCell(r.ls)}</td>
    </tr>`;
  });
  tb.innerHTML=html;
  tb.__list=list;
}

// ---- expandable verdict rows ----
function toggle(tr){
  const nx=tr.nextElementSibling;
  if(nx && nx.classList.contains('detail')){ nx.remove(); tr.setAttribute('aria-expanded','false'); return; }
  tb.querySelectorAll('tr.detail').forEach(d=>d.remove());
  tb.querySelectorAll('tr.row[aria-expanded="true"]').forEach(d=>d.setAttribute('aria-expanded','false'));
  const r=tb.__list[+tr.dataset.k], v=fams[r.f]||['',''];
  const d=document.createElement('tr');
  d.className='detail';
  d.innerHTML=`<td colspan="12"><div class="det">
    <div class="s"><h4>Strongest side</h4><p>${esc(v[0])}</p></div>
    <div class="w"><h4>Weakest side</h4><p>${esc(v[1])}</p></div>
    <div class="meta">
      <span>${esc(r.pb||'no published rate')}</span>
      <a href="https://fal.ai/models/${r.i}" target="_blank" rel="noopener">open on fal.ai &nearr;</a>
    </div></div></td>`;
  tr.after(d);
  tr.setAttribute('aria-expanded','true');
}
tb.addEventListener('click',e=>{const tr=e.target.closest('tr.row'); if(tr) toggle(tr);});
tb.addEventListener('keydown',e=>{
  if(e.key!=='Enter'&&e.key!==' ')return;
  const tr=e.target.closest('tr.row'); if(tr){e.preventDefault(); toggle(tr);}
});

// ---- search + reset ----
let debounce;
document.getElementById('q').addEventListener('input',e=>{
  clearTimeout(debounce);
  const v=e.target.value.trim().toLowerCase();
  debounce=setTimeout(()=>{st.q=v; render();},110);
});
document.getElementById('reset').addEventListener('click',()=>{
  FACETS.forEach(f=>f.reset());
  RANGES.forEach(rg=>rg.reset());
  st.q='';
  document.getElementById('q').value='';
  closePanels();
  render();
});

render();
