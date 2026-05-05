'use strict';
let charts={},city=getCurrentCity();
Chart.defaults.color='#94a3b8';Chart.defaults.borderColor='rgba(99,179,237,.08)';
Chart.defaults.font.family="'JetBrains Mono',monospace";Chart.defaults.font.size=11;
const $=id=>document.getElementById(id);
const txt=(id,v)=>{const e=$(id);if(e)e.textContent=v};
const htm=(id,h)=>{const e=$(id);if(e)e.innerHTML=h};
async function api(p){const r=await fetch(p);if(!r.ok)throw new Error(r.status);return r.json()}

function renderEvents(events){
  if(!events.length){htm('ncEvents','<div style="color:var(--success);font-size:.82rem;padding:8px">✅ No sudden weather changes detected in the next 90 minutes.</div>');return;}
  htm('ncEvents',events.map(e=>`
    <div class="nowcast-event ${e.severity}">
      <span class="nowcast-icon">${e.icon}</span>
      <div class="nowcast-body">
        <div class="nowcast-title">${e.title}</div>
        <div class="nowcast-detail">${e.detail}</div>
        <div class="nowcast-meta">
          <span class="nowcast-eta">⏱ ETA: ~${e.eta_min} min</span>
          <span class="nowcast-conf">Confidence: ${e.confidence}%</span>
        </div>
      </div>
    </div>`).join(''));
}

function renderTrends(trends,current){
  const arrow=v=>v>0.2?'↑':v<-0.2?'↓':'→';
  const col=v=>v>0.2?'#f43f5e':v<-0.2?'#10b981':'#94a3b8';
  htm('ncTrends',`
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      ${[
        {lbl:'Temperature trend',v:trends.temp_trend,unit:'°C/hr'},
        {lbl:'Pressure trend',v:trends.pressure_trend,unit:'hPa/hr'},
        {lbl:'Wind trend',v:trends.wind_trend,unit:'km/h per hr'},
      ].map(({lbl,v,unit})=>`
        <div style="background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:8px;padding:12px">
          <div style="font-size:.68rem;color:var(--text-3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.06em">${lbl}</div>
          <div style="font-size:1.3rem;font-weight:700;font-family:var(--mono);color:${col(v)}">${arrow(v)} ${v>0?'+':''}${(v||0).toFixed(2)}</div>
          <div style="font-size:.68rem;color:var(--text-3);margin-top:2px">${unit}</div>
        </div>`).join('')}
      <div style="background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:8px;padding:12px">
        <div style="font-size:.68rem;color:var(--text-3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.06em">Current Rain</div>
        <div style="font-size:1.3rem;font-weight:700;font-family:var(--mono);color:var(--accent)">${current.rain||0} mm</div>
        <div style="font-size:.68rem;color:var(--text-3);margin-top:2px">in last hour</div>
      </div>
    </div>`);
}

function renderProjectionChart(projections){
  if(charts.nc)charts.nc.destroy();
  if(!projections.length)return;
  const labels=projections.map(p=>'+'+p.minutes+'m');
  const opts={responsive:true,maintainAspectRatio:false,animation:{duration:500},interaction:{mode:'index',intersect:false},plugins:{legend:{display:true,labels:{color:'#94a3b8',boxWidth:10,padding:14}},tooltip:{backgroundColor:'rgba(10,20,40,.95)',padding:10}},scales:{x:{grid:{color:'rgba(99,179,237,.06)'},ticks:{color:'#94a3b8'}},y:{grid:{color:'rgba(99,179,237,.06)'}}}};
  charts.nc=new Chart($('ncChart'),{type:'line',data:{labels,datasets:[
    {label:'Temp °C',data:projections.map(p=>p.temp),borderColor:'#06b6d4',backgroundColor:'rgba(6,182,212,.1)',borderWidth:2,pointRadius:4,fill:true,tension:.4},
    {label:'Wind km/h',data:projections.map(p=>p.wind),borderColor:'#10b981',backgroundColor:'transparent',borderWidth:2,pointRadius:4,fill:false,tension:.4,borderDash:[4,3]},
  ]},options:opts});
}

function renderPressureChart(obs){
  if(charts.press)charts.press.destroy();
  if(!obs || obs.length < 1) return;
  const labels=obs.slice(-12).map((_,i)=>`-${(11-i)*1}h`);
  const pressures=obs.slice(-12).map(o=>o.pressure||1013);
  charts.press=new Chart($('pressureChart'),{type:'line',data:{labels,datasets:[{
    label:'Pressure hPa',data:pressures,
    borderColor:'#8b5cf6',backgroundColor:'rgba(139,92,246,.1)',
    borderWidth:2,pointRadius:3,fill:true,tension:.4
  }]},options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},plugins:{legend:{display:false},tooltip:{backgroundColor:'rgba(10,20,40,.95)',padding:10}},scales:{x:{grid:{color:'rgba(99,179,237,.06)'}},y:{grid:{color:'rgba(99,179,237,.06)'},title:{display:true,text:'hPa',color:'#94a3b8'}}}}});
}

async function loadNowcast(){
  setLoader(true,'Running nowcast analysis…');
  try{
    const r=await api(`/api/intelligence/nowcast?city=${encodeURIComponent(city)}`);
    if(!r.success)throw new Error(r.error);
    const d=r.data;
    txt('nc-anomaly',d.anomaly_score??'--');
    txt('nc-events',d.events?.length??0);
    txt('nc-temp',(d.current?.temp??'--')+'°C');
    txt('nc-pressure',(d.current?.pressure??'--')+' hPa');
    txt('nc-wind',(d.current?.wind??'--')+' km/h');
    renderEvents(d.events||[]);
    if(d.trends)renderTrends(d.trends,d.current||{});
    if(d.projections?.length)renderProjectionChart(d.projections);
    applyWeatherBackground(d.current_weather?.weather_main||'Clear');
    
    // 🔥 NAYA: Voice summary with 2 second delay
    setTimeout(() => {
        speakNowcast(d);
    }, 2000);

    showToast('Nowcast updated','success');
  }catch(e){showToast(e.message,'error')}
  finally{setLoader(false)}
}

// ─── 🗣️ NOWCAST VOICE ENGINE (ZIDDI HINDI) ──────────────────────────────────
function speakNowcast(data) {
    if (!data) return;
    window.speechSynthesis.cancel(); 

    let script = `${city} के लिए तत्काल पूर्वानुमान। `;
    
    // 1. Trends
    if (data.trends) {
        const t = data.trends;
        if (t.temp_trend > 0.2) script += "अगले कुछ घंटों में गर्मी बढ़ सकती है। ";
        else if (t.temp_trend < -0.2) script += "तापमान में गिरावट होने वाली है। ";
        
        if (t.wind_trend > 2) script += "हवा की रफ़्तार तेज़ होने की संभावना है। ";
    }

    // 2. Anomaly
    if (data.anomaly_score > 70) {
        script += "सावधान! अभी माउसमी बदलाव असामान्य हैं। ";
    }

    // 3. Events
    if (data.events && data.events.length > 0) {
        script += `अगले 90 मिनट में ${data.events.length} बदलाव देखे गए हैं। `;
        const first = data.events[0];
        script += `सबसे मुख्य बदलाव: ${first.title} है, जो लगभग ${first.eta_min} मिनट में शुरू हो सकता है। ${first.detail}। `;
    } else {
        script += "अगले 90 मिनट में मौसम में किसी बड़े बदलाव की संभावना नहीं है। ";
    }

    script += "अपडेट्स के लिए रडार चेक करते रहें।";

    // Chunking for stability
    const chunks = script.split(/[।!?.|]/g).map(s => s.trim()).filter(s => s.length > 2);
    
    let i = 0;
    const voices = window.speechSynthesis.getVoices();
    const hindi = voices.find(v => v.lang.includes('hi') || v.name.toLowerCase().includes('hindi'));

    function nextChunk() {
        if (i >= chunks.length) return;
        const u = new SpeechSynthesisUtterance(chunks[i]);
        u.lang = 'hi-IN';
        u.rate = 0.9;
        if (hindi) u.voice = hindi;
        u.onend = () => { i++; nextChunk(); };
        u.onerror = () => { i++; nextChunk(); };
        window.speechSynthesis.speak(u);
    }

    if (voices.length === 0) {
        window.speechSynthesis.onvoiceschanged = nextChunk;
    } else {
        nextChunk();
    }
}

window.loadNowcast=loadNowcast;

document.addEventListener('DOMContentLoaded',()=>{
  loadNowcast();
  window.addEventListener('cityChange',e=>{city=e.detail.city;loadNowcast();});
  setInterval(loadNowcast,3*60*1000);
});