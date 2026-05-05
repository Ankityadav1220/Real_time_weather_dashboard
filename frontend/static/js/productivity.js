'use strict';
let windowChart = null, cogChart = null;

window.addEventListener('wiq:location', loadProductivity);
document.addEventListener('DOMContentLoaded', loadProductivity);

async function loadProductivity() {
  const params = window.locationParams();
  try {
    const r = await fetch(`/api/intelligence/productivity?${params}`);
    const d = await r.json();
    if (d.success && d.data) {
        renderProductivity(d.data);
        // 🔥 NAYA: Voice trigger with 2 second delay
        setTimeout(() => {
            speakProductivity(d.data);
        }, 2000);
    }
  } catch(e) { console.error('[productivity] error:', e); }
}

function renderProductivity(data) {
  const scores  = data.scores  || {};
  const ctx     = data.context || {};
  const windows = data.windows || [];
  const recs    = data.recommendations || [];

  setText('p-cognitive', scores.cognitive != null ? Math.round(scores.cognitive) + '%' : '--%');
  setText('p-energy',    scores.energy    != null ? Math.round(scores.energy)    + '%' : '--%');
  setText('p-mood',      scores.mood      != null ? Math.round(scores.mood)      + '%' : '--%');
  setText('p-overall',   scores.overall   != null ? Math.round(scores.overall)   + '%' : '--%');
  setText('p-circadian', ctx.circadian_phase || '--');

  ['cityName','currentCity','locationDisplay'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = data.city || window.WIQ.displayName || '--';
  });

  // Performance score bars logic (Unchanged)
  const scoreEl = document.getElementById('prodScores');
  if (scoreEl) {
    const scoreMap = [
      { label: 'Cognitive', val: scores.cognitive, color: 'var(--accent)' },
      { label: 'Energy',    val: scores.energy,    color: 'var(--success)' },
      { label: 'Mood',      val: scores.mood,       color: 'var(--warning)' },
      { label: 'Overall',   val: scores.overall,   color: 'var(--danger)' },
    ];
    scoreEl.innerHTML = scoreMap.map(s => `
      <div>
        <div style="display:flex;justify-content:space-between;font-size:.8rem;margin-bottom:4px">
          <span style="color:var(--text-2)">${s.label}</span>
          <span style="font-weight:600;color:${s.color}">${s.val != null ? Math.round(s.val) + '%' : '--'}</span>
        </div>
        <div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden">
          <div style="height:100%;width:${s.val || 0}%;background:${s.color};border-radius:3px;transition:width .9s ease"></div>
        </div>
      </div>`).join('');
  }

  // Weather context render (Unchanged)
  const ctxEl = document.getElementById('prodContext');
  if (ctxEl) {
    ctxEl.innerHTML = Object.entries(ctx).filter(([k]) => k !== 'circadian_phase').map(([k, v]) => `
      <div style="display:flex;gap:6px">
        <span style="color:var(--accent)">•</span>
        <span>${v}</span>
      </div>`).join('');
  }

  // Focus window timeline render (Unchanged)
  const timeline = document.getElementById('windowTimeline');
  if (timeline && windows.length) {
    const now = new Date().getHours();
    timeline.innerHTML = windows.slice(0, 12).map(w => {
      const isCurrent = w.hour_int === now;
      const c = w.label === 'Peak' ? '#10b981' : w.label === 'Good' ? '#3b82f6' : w.label === 'Moderate' ? '#f59e0b' : '#94a3b8';
      return `<div style="display:flex;flex-direction:column;align-items:center;gap:3px${isCurrent?' font-weight:700':''}" title="${w.label}">
        <div style="height:${Math.max(8, (w.score/100)*40)}px;width:20px;background:${c};border-radius:3px 3px 0 0;min-height:8px;transition:height .5s ease"></div>
        <div style="font-size:.62rem;color:${isCurrent?'var(--accent)':'var(--text-3)'}">${w.hour}</div>
      </div>`;
    }).join('');
  }

  // Recommendations render (Unchanged)
  const recsEl = document.getElementById('prodRecs');
  if (recsEl && recs.length) {
    recsEl.innerHTML = recs.map(rec => `
      <div style="padding:12px;border-radius:8px;background:var(--bg-card-2,var(--bg-secondary))">
        <div style="font-weight:600;font-size:.88rem;margin-bottom:4px">${rec.title || rec}</div>
        ${rec.detail ? `<div style="font-size:.78rem;color:var(--text-2)">${rec.detail}</div>` : ''}
      </div>`).join('');
  } else if (recsEl) {
    const tips = [];
    if ((scores.cognitive || 0) < 50) tips.push({ title: '🧠 Low Cognitive Performance', detail: 'Take a short walk or drink water to boost focus.' });
    if ((scores.mood || 0) < 50)      tips.push({ title: '😊 Mood Booster', detail: 'Step into natural light if possible.' });
    if ((scores.energy || 0) < 40)    tips.push({ title: '⚡ Energy Advice', detail: 'Avoid heavy meals and stay hydrated.' });
    if (!tips.length) tips.push({ title: '✅ Great Conditions', detail: 'Weather conditions are favourable for productivity today!' });
    recsEl.innerHTML = tips.map(t => `
      <div style="padding:12px;border-radius:8px;background:var(--bg-card-2,var(--bg-secondary))">
        <div style="font-weight:600;font-size:.88rem;margin-bottom:4px">${t.title}</div>
        <div style="font-size:.78rem;color:var(--text-2)">${t.detail}</div>
      </div>`).join('');
  }

  // Charts render (Unchanged)
  const canvas = document.getElementById('cogChart');
  if (canvas && windows.length) {
    if (cogChart) { cogChart.destroy(); cogChart = null; }
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const tc = isDark ? '#94a3b8' : '#475569';
    const gc = isDark ? 'rgba(255,255,255,.07)' : 'rgba(0,0,0,.07)';
    cogChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: windows.map(w => w.hour),
        datasets: [{ label: 'Focus Score', data: windows.map(w => w.score),
          borderColor: 'var(--accent)', backgroundColor: 'rgba(99,102,241,.1)',
          borderWidth: 2, tension: .4, fill: true, pointRadius: 3 }]
      },
      options: { responsive: true, maintainAspectRatio: false,
        scales: { x: { ticks: { color: tc, maxTicksLimit: 8 }, grid: { color: gc } },
                  y: { min: 0, max: 100, ticks: { color: tc }, grid: { color: gc } } },
        plugins: { legend: { display: false } } }
    });
  }

  const wCanvas = document.getElementById('windowChart');
  if (wCanvas && windows.length) {
    if (windowChart) { windowChart.destroy(); windowChart = null; }
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const tc = isDark ? '#94a3b8' : '#475569';
    const gc = isDark ? 'rgba(255,255,255,.07)' : 'rgba(0,0,0,.07)';
    const colors = windows.map(w =>
      w.label === 'Peak' ? '#10b981' : w.label === 'Good' ? '#3b82f6' : w.label === 'Moderate' ? '#f59e0b' : '#94a3b8');
    windowChart = new Chart(wCanvas, {
      type: 'bar',
      data: {
        labels: windows.slice(0,12).map(w => w.hour),
        datasets: [{ label: 'Focus', data: windows.slice(0,12).map(w => w.score),
          backgroundColor: colors.slice(0,12), borderRadius: 3 }]
      },
      options: { responsive: true, maintainAspectRatio: false,
        scales: { x: { ticks: { color: tc, font:{size:9} }, grid: { color: gc } },
                  y: { min: 0, max: 100, ticks: { color: tc }, grid: { color: gc } } },
        plugins: { legend: { display: false } } }
    });
  }
}

// ─── 🗣️ PRODUCTIVITY VOICE ENGINE (ZIDDI HINDI) ─────────────────────────────
function speakProductivity(data) {
    if (!data || !data.scores) return;
    window.speechSynthesis.cancel(); 

    const city = data.city || "आपके इलाके";
    const overall = Math.round(data.scores.overall || 0);
    const cognitive = Math.round(data.scores.cognitive || 0);
    const mood = Math.round(data.scores.mood || 0);
    const phase = data.context?.circadian_phase || "सामान्य";

    let script = `${city} की प्रोडक्टिविटी रिपोर्ट। अभी आपका ओवरऑल फोकस स्कोर ${overall} प्रतिशत है। `;
    script += `मौसम के हिसाब से आपका दिमाग और फोकस ${cognitive} प्रतिशत पर है, और मूड स्कोर ${mood} है। `;
    
    if (overall > 75) {
        script += "आज का मौसम काम करने के लिए बहुत बेहतरीन है। अपना सबसे जरूरी काम अभी निपटा लें। ";
    } else if (overall > 50) {
        script += "काम करने के लिए स्थिति सामान्य है। थोड़े ब्रेक के साथ आगे बढ़ें। ";
    } else {
        script += "अभी आपका फोकस कम रह सकता है। थोड़े आराम के बाद काम शुरू करना बेहतर होगा। ";
    }

    if (data.recommendations && data.recommendations.length > 0) {
        const topRec = data.recommendations[0];
        script += `मुख्य सलाह यह है कि: ${topRec.title || topRec}। `;
    }

    script += "फोकस बनाए रखें और अच्छा काम करें।";

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

function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }