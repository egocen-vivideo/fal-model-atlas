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
    const q=s.replace(/^No\s*[\u2014\-]?\s*/,'').replace(/^\((.*)\)$/,'$1').trim();
    return `<span class="no">No${q?' <span class="dim">&middot; '+esc(q)+'</span>':''}</span>`;
  }
  if(/^(Partial|Input only)/i.test(s)) return `<span class="part">${esc(s)}</span>`;
  const q=s.replace(/^Yes\s*[\u2014\-]?\s*/,'').trim();
  return `<span class="yes">Yes</span>${q?' <span class="dim">'+esc(q)+'</span>':''}`;
}
const TYPE={t2v:['b-t2v','T2V'],i2v:['b-i2v','I2V'],ref:['b-ref','REF']};

// ---- stats ----
const priced = rows.filter(r=>r.p!=null).map(r=>r.p).sort((a,b)=>a-b);
const stats=[
  ['332','Endpoints'],
  ['132 / 200','Text&rarr;V / Image&rarr;V'],
  [String(rows.filter(r=>r.c==='ref').length),'Reference&rarr;V'],
  [String(new Set(rows.map(r=>r.f)).size),'Model families'],
  [String(rows.filter(r=>/^Yes/.test(r.au)).length),'Generate audio'],
  [String(rows.filter(r=>/^Yes/.test(r.ls)).length),'Do lipsync'],
  [String(rows.filter(r=>/^Yes/.test(r.e)).length),'Take an end frame'],
  [String(rows.filter(r=>/^Yes/.test(r.m)).length),'Multi&#8209;shot'],
  ['$'+priced[0].toFixed(2)+'&ndash;$'+priced[priced.length-1].toFixed(0),'$/min range'],
];
document.getElementById('stats').innerHTML = stats
  .map(([n,k])=>`<div class="stat"><span class="n">${n}</span><span class="k">${k}</span></div>`).join('');

// ---- state ----
const st={q:'',types:new Set(),caps:new Set(),sort:'fam'};
const tb=document.getElementById('tb'), cnt=document.getElementById('count');

function match(r){
  if(st.types.size && !st.types.has(r.c)) return false;
  for(const c of st.caps){ if(!/^Yes/.test(r[c]||'')) return false; }
  if(st.q){
    const h=(r.i+' '+r.f+' '+r.l+' '+r.ds).toLowerCase();
    if(!st.q.split(/\s+/).every(t=>h.includes(t))) return false;
  }
  return true;
}

function render(){
  let list=rows.filter(match);
  const s=st.sort;
  if(s==='pa') list.sort((a,b)=>(a.p==null)-(b.p==null)||a.p-b.p);
  else if(s==='pd') list.sort((a,b)=>(a.p==null)-(b.p==null)||b.p-a.p);
  else if(s==='fd') list.sort((a,b)=>(b.mf||0)-(a.mf||0));
  else if(s==='id') list.sort((a,b)=>a.i.localeCompare(b.i));
  else list.sort((a,b)=>a.f.localeCompare(b.f)||a.i.localeCompare(b.i));

  cnt.textContent=`${list.length} of ${rows.length} endpoints`;
  if(!list.length){ tb.innerHTML='<tr><td colspan="12"><div class="empty">No model matches those filters.</div></td></tr>'; return; }

  const grouped = s==='fam';
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

// ---- expand ----
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

// ---- controls ----
let t;
document.getElementById('q').addEventListener('input',e=>{
  clearTimeout(t); const v=e.target.value.trim().toLowerCase();
  t=setTimeout(()=>{st.q=v; render();},110);
});
document.getElementById('sort').addEventListener('change',e=>{st.sort=e.target.value; render();});
function chipGroup(id,key,setName){
  document.getElementById(id).addEventListener('click',e=>{
    const b=e.target.closest('.chip'); if(!b)return;
    const v=b.dataset[key], on=b.getAttribute('aria-pressed')==='true';
    b.setAttribute('aria-pressed',String(!on));
    on?st[setName].delete(v):st[setName].add(v);
    render();
  });
}
chipGroup('typechips','type','types');
chipGroup('capchips','cap','caps');

render();
