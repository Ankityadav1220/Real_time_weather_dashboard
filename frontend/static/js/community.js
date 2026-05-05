/* community.js */
'use strict';
let city=getCurrentCity();
const $=id=>document.getElementById(id);
const txt=(id,v)=>{const e=$(id);if(e)e.textContent=v};
const htm=(id,h)=>{const e=$(id);if(e)e.innerHTML=h};
async function api(p,o){const r=await fetch(p,o||{});if(!r.ok)throw new Error(r.status);return r.json()}

const TYPE_ICONS={rain:'🌧️',flood:'🌊',fog:'🌫️',heatwave:'🌡️',storm:'⛈️',clear:'☀️',other:'📍'};
const SEV_COLORS={mild:'#10b981',moderate:'#f59e0b',severe:'#f97316',extreme:'#f43f5e'};

async function submitReport(){
  const c=$('rptCity')?.value||city;
  const type=$('rptType')?.value||'rain';
  const sev=$('rptSev')?.value||'moderate';
  const note=$('rptNote')?.value||'';
  try{
    const r=await api('/api/intelligence/community-report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({city:c,type,severity:sev,note})});
    if(r.success){showToast('Report submitted! Thank you 🙏','success');if($('rptNote'))$('rptNote').value='';loadReports();}
    else showToast(r.error||'Submission failed','error');
  }catch(e){showToast(e.message,'error')}
}
window.submitReport=submitReport;

async function loadReports(){
  try{
    const r=await api(`/api/intelligence/community-reports?city=${encodeURIComponent(city)}`);
    const reports=r.reports||[];
    if(!reports.length){htm('reportsList','<div style="color:var(--text-3);font-size:.82rem;padding:10px">No community reports yet for this city. Be the first to submit one!</div>');return;}
    htm('reportsList',reports.map(rep=>{
      const icon=TYPE_ICONS[rep.report_type]||'📍';
      const col=SEV_COLORS[rep.severity]||'#94a3b8';
      const time=new Date(rep.reported_at).toLocaleString();
      return`<div style="background:rgba(255,255,255,.04);border:1px solid var(--border);border-left:3px solid ${col};border-radius:8px;padding:12px 14px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
          <span style="font-size:1.1rem">${icon}</span>
          <span style="font-size:.85rem;font-weight:600;text-transform:capitalize">${rep.report_type}</span>
          <span style="margin-left:auto;font-size:.68rem;background:rgba(255,255,255,.06);border:1px solid ${col};color:${col};border-radius:10px;padding:2px 8px;font-weight:600">${rep.severity}</span>
        </div>
        ${rep.note?`<div style="font-size:.78rem;color:var(--text-2);margin-bottom:4px">${rep.note}</div>`:''}
        <div style="font-size:.65rem;color:var(--text-3)">${rep.city} · ${time}</div>
      </div>`;
    }).join(''));

    // Build comparison
    const typeCounts={};
    reports.forEach(r=>{typeCounts[r.report_type]=(typeCounts[r.report_type]||0)+1;});
    const topType=Object.entries(typeCounts).sort((a,b)=>b[1]-a[1])[0];
    htm('comparisonPanel',`
      <div style="font-size:.82rem;color:var(--text-2);line-height:1.7">
        <div>📊 <strong>${reports.length}</strong> community reports for <strong>${city}</strong></div>
        ${topType?`<div>🔝 Most reported: <strong>${TYPE_ICONS[topType[0]]||'📍'} ${topType[0]}</strong> (${topType[1]} reports)</div>`:''}
        <div style="margin-top:10px;font-size:.78rem;color:var(--text-3)">Community reports help validate API predictions and improve AI accuracy for your area.</div>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:10px">
        ${Object.entries(typeCounts).map(([t,c])=>`<span style="background:rgba(255,255,255,.05);border:1px solid var(--border);border-radius:20px;padding:3px 10px;font-size:.72rem">${TYPE_ICONS[t]||'📍'} ${t}: ${c}</span>`).join('')}
      </div>`);
  }catch(e){htm('reportsList',`<div style="color:var(--danger);font-size:.82rem">${e.message}</div>`);}
}
window.loadReports=loadReports;

document.addEventListener('DOMContentLoaded',()=>{
  if($('rptCity'))$('rptCity').value=city;
  loadReports();
  window.addEventListener('cityChange',e=>{city=e.detail.city;if($('rptCity'))$('rptCity').value=city;loadReports();});
});
