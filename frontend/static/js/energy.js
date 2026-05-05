'use strict';
let energyChart = null;

window.addEventListener('wiq:location', loadEnergy);
document.addEventListener('DOMContentLoaded', loadEnergy);

async function loadEnergy() {
  const params = window.locationParams();
  try {
    const r = await fetch(`/api/intelligence/energy?${params}`);
    const d = await r.json();
    if (d.success && d.data) {
        renderEnergy(d.data);
        
        // 🔥 NAYA: Voice trigger with 2 second delay
        setTimeout(() => {
            speakEnergyAI(d.data);
        }, 2000);
    }
  } catch(e) { console.error('[energy] error:', e); }
}

function renderEnergy(data) {
  setText('en-kwh',       data.current_kwh   != null ? data.current_kwh.toFixed(1)   : '--');
  setText('en-daily',     data.daily_est_kwh != null ? data.daily_est_kwh.toFixed(1)  : '--');
  setText('en-cost',       data.cost_per_hour != null ? data.cost_per_hour.toFixed(0)  : '--');
  setText('en-daily-cost', data.daily_cost_inr!= null ? data.daily_cost_inr.toFixed(0) : '--');
  setText('en-solar',      data.solar_potential_pct != null ? data.solar_potential_pct + '%' : '--%');

  const bar = document.getElementById('solarBar');
  if (bar) bar.style.width = (data.solar_potential_pct || 0) + '%';

  ['cityName','currentCity','locationDisplay'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = data.city || window.WIQ.displayName || '--';
  });

  // Breakdown render logic (Unchanged)
  const breakdown = document.getElementById('enBreakdown');
  if (breakdown && data.breakdown) {
    breakdown.innerHTML = Object.entries(data.breakdown).map(([k, v]) => `
      <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border)">
        <span style="font-size:.82rem;color:var(--text-2);min-width:80px;text-transform:capitalize">${k.replace(/_/g,' ')}</span>
        <div style="flex:1;height:5px;background:var(--border);border-radius:3px;overflow:hidden">
          <div style="height:100%;width:${Math.min(100, (v / (data.current_kwh || 1)) * 100)}%;background:var(--warning);border-radius:3px"></div>
        </div>
        <span style="font-size:.82rem;font-weight:600;color:var(--warning);min-width:50px;text-align:right">${v.toFixed(2)} kWh</span>
      </div>`).join('');
  }

  // Tips render logic (Unchanged)
  const tips = document.getElementById('enTips');
  if (tips && data.tips) {
    tips.innerHTML = data.tips.map(t => `
      <div style="display:flex;gap:8px;align-items:flex-start">
        <span>${t.icon || '💡'}</span>
        <span style="font-size:.82rem;color:var(--text-2)">${t.text}</span>
      </div>`).join('');
  }

  // Savings recommendations render logic (Unchanged)
  const save = document.getElementById('energySave');
  if (save && data.tips) {
    save.innerHTML = data.tips.map(t => `
      <div style="padding:12px;border-radius:8px;background:var(--bg-card-2,var(--bg-secondary));display:flex;gap:10px">
        <span style="font-size:1.4rem">${t.icon || '💡'}</span>
        <span style="font-size:.83rem;color:var(--text)">${t.text}</span>
      </div>`).join('');
  }

  // Chart render logic (Unchanged)
  const canvas = document.getElementById('energyChart');
  if (canvas && data.hourly_forecast?.length) {
    if (energyChart) { energyChart.destroy(); energyChart = null; }
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const tc = isDark ? '#94a3b8' : '#475569';
    const gc = isDark ? 'rgba(255,255,255,.07)' : 'rgba(0,0,0,.07)';
    energyChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: data.hourly_forecast.map(h => h.hour),
        datasets: [
          { label: 'kWh', data: data.hourly_forecast.map(h => h.kwh),
            borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,.1)',
            borderWidth: 2, tension: .4, fill: true, pointRadius: 3, yAxisID: 'y' },
          { label: '₹ Cost', data: data.hourly_forecast.map(h => h.cost),
            borderColor: '#ef4444', borderWidth: 2, tension: .4, pointRadius: 2, yAxisID: 'y1' }
        ]
      },
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: tc, font:{size:11} } } },
        scales: {
          x: { ticks: { color: tc }, grid: { color: gc } },
          y: { ticks: { color: tc }, grid: { color: gc }, title: { display:true, text:'kWh', color:tc } },
          y1: { position: 'right', ticks: { color: tc }, grid: { drawOnChartArea:false }, title: { display:true, text:'₹', color:tc } }
        }
      }
    });
  }
}

// ─── 🗣️ ENERGY AI VOICE ENGINE (ZIDDI HINDI) ──────────────────────────────────
function speakEnergyAI(data) {
    if (!data) return;
    window.speechSynthesis.cancel(); 

    const city = data.city || "आपके इलाके";
    const kwh = data.current_kwh != null ? data.current_kwh.toFixed(1) : "0";
    const cost = data.daily_cost_inr != null ? Math.round(data.daily_cost_inr) : "0";
    const solar = data.solar_potential_pct || 0;

    let script = `${city} की एनर्जी रिपोर्ट। अभी आपकी अनुमानित बिजली खपत ${kwh} यूनिट प्रति घंटा है। `;
    script += `आज का कुल अनुमानित बिजली खर्चा लगभग ${cost} रुपये हो सकता है। `;
    
    if (solar > 75) {
        script += `आज धूप बहुत अच्छी है, सोलर ऊर्जा बनाने के लिए बेहतरीन दिन है। `;
    } else if (solar > 45) {
        script += `आज सोलर ऊर्जा बनाने के लिए स्थिति सामान्य है। `;
    } else {
        script += `आज धूप कम होने के कारण सोलर ऊर्जा कम बनेगी। `;
    }

    if (data.tips && data.tips.length > 0) {
        script += `बिजली बचाने की सलाह: ${data.tips[0].text}। `;
    }

    script += "बिजली बचाएं, पैसे बचाएं।";

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