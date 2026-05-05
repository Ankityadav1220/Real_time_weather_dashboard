'use strict';
let healthChart = null;

window.addEventListener('wiq:location', loadHealth);
document.addEventListener('DOMContentLoaded', loadHealth);

async function loadHealth() {
  const params = window.locationParams();
  const age  = document.getElementById('hiAge')?.value  || 'adult';
  const conds = [...(document.getElementById('hiCond')?.selectedOptions || [])].map(o => o.value);
  const extra = `age_group=${age}&conditions=${encodeURIComponent(conds.join(','))}`;
  try {
    const r = await fetch(`/api/intelligence/health-impact?${params}&${extra}`);
    const d = await r.json();
    if (d.success && d.data) {
        renderHealth(d.data);
        // 🔥 NAYA: Voice trigger with 2 second delay
        setTimeout(() => {
            speakHealthImpact(d.data);
        }, 2000);
    }
  } catch(e) { console.error('[health_impact] error:', e); }
}

function renderHealth(data) {
  const w = data.weather || {};
  const impacts = data.impacts || {};
  const aqi = w.aqi_info || {};

  setText('hi-overall', data.overall_score != null ? data.overall_score + '/100' : '--');
  setText('hi-temp',     (w.temperature != null ? w.temperature : '--') + '°C');
  setText('hi-hum',      (w.humidity != null ? w.humidity : '--') + '%');
  setText('hi-aqi',      aqi.label || (w.aqi_info ? 'L' + aqi.value : '--'));

  ['cityName','currentCity','locationDisplay'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = data.city || window.WIQ.displayName || '--';
  });

  const grid = document.getElementById('healthGrid');
  if (grid) {
    grid.innerHTML = Object.entries(impacts).map(([key, h]) => `
      <div style="padding:14px;border-radius:8px;background:var(--bg-card-2,var(--bg-secondary));border-left:4px solid ${h.color || '#94a3b8'}">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:1.3rem">${h.icon || '🏥'}</span>
          <span style="font-weight:600;font-size:.9rem">${h.title || key}</span>
          <span style="margin-left:auto;background:${h.color};color:#fff;font-size:.72rem;padding:2px 8px;border-radius:10px">${h.level || '--'}</span>
        </div>
        <div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden;margin-bottom:8px">
          <div style="height:100%;width:${h.score || 0}%;background:${h.color};border-radius:3px;transition:width .9s ease"></div>
        </div>
        <div style="font-size:.78rem;color:var(--text-2)">${h.detail || ''}</div>
      </div>`
    ).join('');
  }

  const canvas = document.getElementById('healthChart');
  if (canvas && Object.keys(impacts).length) {
    if (healthChart) { healthChart.destroy(); healthChart = null; }
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const tc = isDark ? '#94a3b8' : '#475569';
    const gc = isDark ? 'rgba(255,255,255,.07)' : 'rgba(0,0,0,.07)';
    healthChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: Object.values(impacts).map(h => h.title),
        datasets: [{ label: 'Risk Score', data: Object.values(impacts).map(h => h.score || 0),
          backgroundColor: Object.values(impacts).map(h => (h.color || '#94a3b8') + 'bb'),
          borderColor: Object.values(impacts).map(h => h.color || '#94a3b8'),
          borderWidth: 2, borderRadius: 4 }]
      },
      options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y',
        scales: { x: { min: 0, max: 100, ticks: { color: tc }, grid: { color: gc } },
                  y: { ticks: { color: tc }, grid: { color: gc } } },
        plugins: { legend: { display: false } } }
    });
  }
}

// ─── 🗣️ HEALTH IMPACT VOICE ENGINE (ZIDDI HINDI) ───────────────────────────
function speakHealthImpact(data) {
    if (!data) return;
    window.speechSynthesis.cancel(); 

    const city = data.city || "आपके इलाके";
    const score = data.overall_score || 0;
    const impacts = data.impacts || {};

    let script = `${city} की स्वास्थ्य रिपोर्ट। आज सेहत पर मौसम का असर पड़ने का स्कोर ${score} है। `;

    if (score > 60) {
        script += `सावधान! आज स्वास्थ्य के लिए स्थिति मध्यम से गंभीर हो सकती है। `;
    } else {
        script += `आज स्वास्थ्य के लिहाज से स्थिति काफी हद तक सुरक्षित है। `;
    }

    // फाइंड टॉप रिस्क
    const sortedImpacts = Object.values(impacts).sort((a, b) => b.score - a.score);
    const top = sortedImpacts[0];

    if (top && top.score > 30) {
        script += `मुख्य सलाह: ${top.title} के लिए खतरा ${top.level} है। ${top.detail}। `;
    }

    script += "खूब पानी पिएं और अपनी सेहत का ध्यान रखें।";

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

function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }