'use strict';
let urbanChart = null;

window.addEventListener('wiq:location', loadUrbanRisk);
document.addEventListener('DOMContentLoaded', loadUrbanRisk);

async function loadUrbanRisk() {
  const params = window.locationParams();
  try {
    const r = await fetch(`/api/intelligence/urban-risk?${params}`);
    const d = await r.json();
    if (d.success && d.data) {
        renderUrbanRisk(d.data);
        // 🔥 NAYA: Voice trigger with 2 second delay
        setTimeout(() => {
            speakUrbanRisk(d.data);
        }, 2000);
    }
  } catch(e) { console.error('[urban_risk] error:', e); }
}

function renderUrbanRisk(data) {
  const w = data.weather || {};
  const risks = data.risks || {};

  setText('ur-overall', data.overall_label || (data.overall_score != null ? data.overall_score + '/100' : '--'));
  setText('ur-rain',    (w.rain_1h != null ? w.rain_1h : '--') + ' mm');
  setText('ur-wind',    (w.wind_speed != null ? w.wind_speed : '--') + ' km/h');
  setText('ur-peak',    data.peak_hours ? '⚠️ Peak Hours' : '✅ Off-peak');

  ['cityName','currentCity','locationDisplay'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = data.city || window.WIQ.displayName || '--';
  });

  const grid = document.getElementById('urbanGrid');
  if (grid) {
    grid.innerHTML = Object.entries(risks).map(([key, r]) => `
      <div class="risk-card" style="border-left:4px solid ${r.color || '#94a3b8'};padding:14px;border-radius:8px;background:var(--bg-card-2,var(--bg-secondary))">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:1.4rem">${r.icon || '⚠️'}</span>
          <span style="font-weight:600;font-size:.9rem">${r.title || key.replace(/_/g,' ')}</span>
          <span style="margin-left:auto;background:${r.color};color:#fff;font-size:.72rem;padding:2px 8px;border-radius:10px">${r.label || '--'}</span>
        </div>
        <div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden;margin-bottom:6px">
          <div style="height:100%;width:${r.score || 0}%;background:${r.color};border-radius:3px;transition:width .9s ease"></div>
        </div>
        <div style="font-size:.78rem;color:var(--text-2)">${r.score ?? '--'}/100</div>
      </div>`
    ).join('');
  }

  const advEl = document.getElementById('urbanAdvisories');
  if (advEl && data.advisories) {
    advEl.innerHTML = data.advisories.map(a => `
      <div style="display:flex;align-items:flex-start;gap:10px;padding:10px;background:var(--bg-card-2,var(--bg-secondary));border-radius:8px">
        <span style="font-size:1.2rem">${a.icon || '📢'}</span>
        <span style="font-size:.85rem;color:var(--text)">${a.text || a.message || ''}</span>
      </div>`).join('');
  }

  const canvas = document.getElementById('urbanChart');
  if (canvas && Object.keys(risks).length) {
    if (urbanChart) { urbanChart.destroy(); urbanChart = null; }
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const tc = isDark ? '#94a3b8' : '#475569';
    urbanChart = new Chart(canvas, {
      type: 'radar',
      data: {
        labels: Object.values(risks).map(r => r.title || ''),
        datasets: [{ label: 'Risk Score', data: Object.values(risks).map(r => r.score || 0),
          backgroundColor: 'rgba(239,68,68,.2)', borderColor: '#ef4444', borderWidth: 2,
          pointBackgroundColor: Object.values(risks).map(r => r.color || '#ef4444'), pointRadius: 4 }]
      },
      options: { responsive: true, maintainAspectRatio: false,
        scales: { r: { min: 0, max: 100, ticks: { color: tc, stepSize: 25, font:{size:10} },
          pointLabels: { color: tc, font:{size:11} }, grid: { color: isDark?'rgba(255,255,255,.1)':'rgba(0,0,0,.1)' } } },
        plugins: { legend: { display: false } } }
    });
  }
}

// ─── 🗣️ URBAN RISK VOICE ENGINE (ZIDDI HINDI) ──────────────────────────────
function speakUrbanRisk(data) {
    if (!data) return;
    window.speechSynthesis.cancel(); 

    const city = data.city || "आपके शहर";
    const label = data.overall_label || "सामान्य";
    const risks = data.risks || {};

    let script = `${city} का शहरी रिस्क रडार। अभी ओवरऑल रिस्क लेवल ${label} है। `;

    // Important Urban Risks
    if (risks.traffic) script += `ट्रैफिक रिस्क अभी ${risks.traffic.label} है। `;
    if (risks.waterlogging && risks.waterlogging.score > 40) {
        script += `सावधान! कुछ इलाकों में जलभराव की संभावना ${risks.waterlogging.label} है। `;
    }

    // Advisories
    if (data.advisories && data.advisories.length > 0) {
        script += "मुख्य सलाह इस प्रकार है। ";
        script += data.advisories.map(a => a.text || a.message).join('। ');
    } else {
        script += "फिलहाल शहर में स्थिति नियंत्रण में है।";
    }

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