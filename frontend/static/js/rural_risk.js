/**
 * WeatherIQ Rural Risk — v19 (Brief Hindi Voice)
 * Features: Only speaks City, Crop Name, and Advisories. 
 * Weather details removed from voice as per user request.
 */
'use strict';

window.addEventListener('wiq:location', () => { loadRuralRisk(); });

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('cropSelect')?.addEventListener('change', loadRuralRisk);
  loadRuralRisk();
});

async function loadRuralRisk() {
  const params = window.locationParams();
  const crop   = document.getElementById('cropSelect')?.value || 'general';
  const loading = document.getElementById('ruralLoading');
  const content = document.getElementById('ruralContent');
  
  if (loading) loading.classList.remove('hidden');
  if (content) content.classList.add('hidden');
  
  try {
    const r = await fetch(`/api/intelligence/rural-risk?${params}&crop=${encodeURIComponent(crop)}`);
    const d = await r.json();
    
    if (d.success && d.data) {
        renderRuralRisk(d.data);
        // Data aate hi crop ki brief salah bolna shuru
        setTimeout(() => {
            speakRuralBrief(d.data, crop);
        }, 1200);
    }
  } catch(e) { console.error(e); }
  finally {
    if (loading) loading.classList.add('hidden');
    if (content) content.classList.remove('hidden');
  }
}

function renderRuralRisk(data) {
  setText('ruralCity', data.city || '--');
  setText('ruralOverall', data.overall_risk_label || '--');
  const risks = data.risks || {};
  Object.entries(risks).forEach(([key, val]) => {
    const el = document.getElementById(`risk-${key}`);
    if (!el) return;
    const score = val.score || '--';
    const detail = val.detail || '';
    el.innerHTML = `<div class="risk-score" style="color:${val.color}">${score}</div>
                    <div class="risk-desc">${detail}</div>`;
  });
  const advEl = document.getElementById('ruralAdvisories');
  if (advEl && data.advisories) {
    advEl.innerHTML = data.advisories.map(a => `
      <div class="advisory-item" style="display:flex; gap:12px; background:var(--surface-1); padding:12px; border-radius:8px; margin-bottom:10px; border-left:4px solid var(--accent);">
        <span style="font-size:1.5rem;">${a.icon}</span>
        <div><strong>${a.title}</strong><p style="margin:0; font-size:0.9rem; color:var(--text-2);">${a.message}</p></div>
      </div>`).join('');
  }
}

// ─── 🗣️ BRIEF HINDI VOICE (CROP & ADVISORIES ONLY) ──────────────────────────
function speakRuralBrief(data, cropName) {
  if (!data || !data.advisories) return;
  
  window.speechSynthesis.cancel(); 

  const city = data.city || "आपके इलाके";
  
  // Hindi names mapping for better voice experience
  const cropMap = { 'wheat': 'गेहूं', 'rice': 'धान', 'corn': 'मक्का', 'general': 'फसलों' };
  const desiCrop = cropMap[cropName.toLowerCase()] || cropName;

  // STEP 1: Sirf City aur Crop ki header line
  let fullScript = `${city} के लिए ${desiCrop} की मुख्य सलाह। `;

  // STEP 2: Saari advisories ko "।" ke saath jodo
  if (data.advisories.length > 0) {
    data.advisories.forEach(a => {
        const msg = a.hindi_msg || a.message || "";
        if (msg.trim().length > 0) {
            fullScript += msg + "। ";
        }
    });
  } else {
    fullScript += "फिलहाल कोई विशेष चेतावनी नहीं है।";
  }

  // Split into chunks for stability (Sentence by sentence)
  const chunks = fullScript.split(/[।!?.|]/g).map(s => s.trim()).filter(s => s.length > 2);
  
  const voices = window.speechSynthesis.getVoices();
  const hindiVoice = voices.find(v => v.lang.includes('hi') || v.name.toLowerCase().includes('hindi'));

  let i = 0;
  function next() {
    if (i >= chunks.length) return;

    const utterance = new SpeechSynthesisUtterance(chunks[i]);
    utterance.lang = 'hi-IN';
    utterance.rate = 0.9; // Normal speed
    if (hindiVoice) utterance.voice = hindiVoice;

    utterance.onend = () => { i++; next(); };
    utterance.onerror = () => { i++; next(); };

    window.speechSynthesis.speak(utterance);
  }

  if (voices.length === 0) {
    window.speechSynthesis.onvoiceschanged = next;
  } else {
    next();
  }
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}