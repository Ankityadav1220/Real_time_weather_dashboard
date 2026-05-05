'use strict';

window.addEventListener('wiq:location', loadSafety);
document.addEventListener('DOMContentLoaded', loadSafety);

async function loadSafety() {
  const params  = window.locationParams();
  const age     = document.getElementById('ageGroup')?.value || 'adult';
  const conds   = [...(document.getElementById('healthCond')?.selectedOptions || [])].map(o => o.value);
  const extra   = `age_group=${age}&conditions=${encodeURIComponent(conds.join(','))}`;
  try {
    const r = await fetch(`/api/intelligence/safety-radar?${params}&${extra}`);
    const d = await r.json();
    if (d.success && d.data) {
        renderSafety(d.data);
        // 🔥 NAYA: Voice trigger with 2 second delay
        setTimeout(() => {
            speakSafetyRadar(d.data);
        }, 2000);
    }
  } catch(e) { console.error('[safety_radar] error:', e); }
}

function renderSafety(data) {
  const risks = data.risks || {};
  const score = data.overall_score ?? 0;
  const color = data.overall_color || '#10b981';

  // Overall ring
  const arc = document.getElementById('overallArc');
  if (arc) {
    const circumference = 402;
    const offset = circumference - (score / 100) * circumference;
    arc.style.stroke = color;
    arc.style.strokeDashoffset = offset;
  }
  const scoreEl = document.getElementById('overallScore');
  if (scoreEl) { scoreEl.textContent = score; scoreEl.style.color = color; }
  setText('overallLevel', data.overall_level || '--');
  const colorEl = document.getElementById('overallColor');
  if (colorEl) { 
      colorEl.textContent = `Dominant risk: ${(data.dominant_risk || '').replace(/_/g,' ')}`; 
      colorEl.style.color = color; 
  }

  ['cityName','currentCity','locationDisplay'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = data.city || window.WIQ.displayName || '--';
  });

  // Risk summary
  const summary = document.getElementById('riskSummary');
  if (summary) {
    const top = Object.entries(risks).filter(([,r]) => r.score > 0).sort((a,b) => b[1].score - a[1].score).slice(0,4);
    if (!top.length) {
      summary.innerHTML = '<div style="color:var(--success);font-size:.85rem">✅ All risk levels are safe.</div>';
    } else {
      summary.innerHTML = top.map(([key, r]) => `
        <div style="display:flex;align-items:center;gap:10px">
          <span style="font-size:.78rem;min-width:110px;color:var(--text-2)">${key.replace(/_/g,' ')}</span>
          <div style="flex:1;height:6px;background:var(--border);border-radius:3px;overflow:hidden">
            <div style="height:100%;width:${r.score}%;background:${r.color};border-radius:3px;transition:width .9s ease"></div>
          </div>
          <span style="font-size:.78rem;color:${r.color};min-width:36px;text-align:right">${r.score}</span>
        </div>`).join('');
    }
  }

  // Risk cards
  const cards = document.getElementById('riskCards');
  if (cards) {
    cards.innerHTML = Object.entries(risks).map(([key, r]) => `
      <div style="padding:14px;border-radius:8px;background:var(--bg-card-2,var(--bg-secondary));border-left:4px solid ${r.color || '#94a3b8'}">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-weight:600;font-size:.9rem;text-transform:capitalize">${key.replace(/_/g,' ')}</span>
          <span style="margin-left:auto;background:${r.color};color:#fff;font-size:.72rem;padding:2px 8px;border-radius:10px">${r.level || '--'}</span>
        </div>
        <div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden;margin-bottom:8px">
          <div style="height:100%;width:${r.score || 0}%;background:${r.color};border-radius:3px;transition:width .9s ease"></div>
        </div>
        <div style="font-size:.78rem;color:var(--text-2)">${r.advice || ''}</div>
      </div>`
    ).join('');
  }

  // Safety advice
  const advEl = document.getElementById('safetyAdvice');
  if (advEl) {
    const high = Object.entries(risks).filter(([,r]) => r.score >= 30).sort((a,b) => b[1].score - a[1].score);
    if (!high.length) {
      advEl.innerHTML = '<div style="color:var(--success);font-size:.85rem;padding:8px">✅ No significant safety concerns. Stay aware of weather changes.</div>';
    } else {
      advEl.innerHTML = high.map(([key, r]) => `
        <div style="padding:12px;border-radius:8px;background:var(--bg-card-2,var(--bg-secondary));border-left:3px solid ${r.color}">
          <div style="font-weight:600;font-size:.88rem;margin-bottom:4px;color:${r.color}">${key.replace(/_/g,' ').toUpperCase()}</div>
          <div style="font-size:.82rem;color:var(--text)">${r.advice}</div>
        </div>`).join('');
    }
  }
}

// ─── 🗣️ SAFETY RADAR VOICE ENGINE ──────────────────────────────────────────
function speakSafetyRadar(data) {
    if (!data) return;
    window.speechSynthesis.cancel(); 

    const city = data.city || "आपके इलाके";
    const score = data.overall_score ?? 0;
    const level = data.overall_level || "सामान्य";
    const domRisk = (data.dominant_risk || "").replace(/_/g, ' ');

    let script = `${city} की सुरक्षा रिपोर्ट। अभी आपका सुरक्षा स्कोर ${score} है और स्थिति ${level} है। `;
    
    if (domRisk) {
        script += `मुख्य खतरा ${domRisk} का है। `;
    }

    // Kuch important advice jodo agar hain toh
    const highRisks = Object.entries(data.risks || {}).filter(([,r]) => r.score >= 50);
    if (highRisks.length > 0) {
        script += "सावधानी के लिए सलाह: ";
        script += highRisks.map(([k, r]) => r.advice).join('। ');
    } else {
        script += "अभी स्थिति सुरक्षित है, फिर भी सावधान रहें।";
    }

    // Split into chunks to prevent browser timeout
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