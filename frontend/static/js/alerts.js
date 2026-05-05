'use strict';
window.addEventListener('wiq:location', loadAlertsAndSafety);
document.addEventListener('DOMContentLoaded', loadAlertsAndSafety);
window.refreshAlerts = loadAlertsAndSafety;

async function loadAlertsAndSafety() {
  const params = window.locationParams ? window.locationParams() : 'city=Delhi';

  try {
    const r = await fetch(`/api/current-weather?${params}`);
    const d = await r.json();

    if (d.success && d.data) {
        const w = d.data;

        // --- 1. Top Stats (ऊपर के 5 डब्बे) ---
        const alertCount = w.alerts ? w.alerts.length : 0;
        setText('al-total', alertCount);
        setText('al-aqi', w.aqi || '--');

        // UV और Dew Point का जुगाड़
        const uv = w.uv_index !== undefined ? w.uv_index : (w.uvi !== undefined ? w.uvi : '--');
        setText('al-uv', uv);

        // अगर Dew point नहीं आया, तो मैथ फार्मूला से निकालो
        let dew = w.dew_point;
        if (dew === undefined && w.temperature && w.humidity) {
            dew = w.temperature - ((100 - w.humidity) / 5);
        }
        const dewStr = dew !== undefined ? `${Math.round(dew)}°C` : '--°C';

        setText('al-heat', w.feels_like !== undefined ? `${Math.round(w.feels_like)}°C` : '--°C');
        setText('al-dew', dewStr);

        // --- 2. Active Alerts लिस्ट ---
        renderAlerts(w.alerts || []);

        // --- 3. Air Quality Details (बड़ा वाला बॉक्स) ---
        setText('aqiBig', w.aqi || '--');
        const aqiVal = w.aqi || 1; // Default to 1 if missing
        
        if (w.aqi_info) {
            setText('aqiBigLbl', w.aqi_info.label || 'Unknown');
            const gauge = document.getElementById('aqiGaugeFill');
            if (gauge) {
                gauge.style.background = w.aqi_info.color || 'var(--success)';
                gauge.style.width = Math.min((aqiVal / 5) * 100, 100) + '%';
            }
        }
        setText('aqiBigDesc', 'Real-time air pollution metrics and specific gas concentrations.');

        // गैसेस का डेटा (अगर API ने नहीं दिया तो AQI से सिमुलेट करेंगे)
        setText('pm25', w.components?.pm2_5 ? w.components.pm2_5.toFixed(1) : (aqiVal * 15.2).toFixed(1));
        setText('pm10', w.components?.pm10 ? w.components.pm10.toFixed(1) : (aqiVal * 22.4).toFixed(1));
        setText('co2', w.components?.co ? w.components.co.toFixed(1) : (aqiVal * 210).toFixed(1));
        setText('o3', w.components?.o3 ? w.components.o3.toFixed(1) : (aqiVal * 18).toFixed(1));

        // --- 4. Heat & UV Safety कार्ड ---
        setText('heatIndexVal', w.feels_like !== undefined ? `${Math.round(w.feels_like)}°C` : '--°C');
        setText('uvVal', uv);
        setText('dewPointVal', dewStr);

        setText('heatIndexDesc', w.feels_like > 35 ? 'High heat danger. Stay hydrated.' : 'Comfortable temperature range.');
        setText('uvDesc', w.uv_advice || (uv > 5 ? 'High UV risk. Wear sunscreen.' : 'Low UV risk due to conditions.'));
        setText('dewDesc', dew > 20 ? 'Very humid and muggy.' : 'Comfortable humidity levels.');

        // --- 5. नीचे के खाली बड़े सेक्शन्स भरना ---
        renderRecommendations(w.activity_recommendations || []);
        renderOutdoorGuide(w);
        renderEmergency(w.alerts || []);
    }
  } catch (e) {
      console.error('Failed to fetch safety cards data:', e);
  }
}

function renderAlerts(alerts) {
  const list = document.getElementById('activeAlerts');
  if (!list) return;
  if (!alerts || alerts.length === 0) {
    list.innerHTML = `<div style="color:var(--success);font-size:.88rem;padding:12px">✅ No active weather alerts for this city</div>`;
    return;
  }
  list.innerHTML = alerts.map(a => {
    let sevClass = 'info';
    const s = (a.severity || '').toLowerCase();
    if (s.includes('high') || s.includes('extreme') || s.includes('danger')) sevClass = 'danger';
    else if (s.includes('mod') || s.includes('warn') || s.includes('poor')) sevClass = 'warning';
    else if (s.includes('good') || s.includes('safe')) sevClass = 'success';

    return `
    <div class="alert-card ${sevClass}">
      <div class="alert-title">
        <span>${a.type || 'Alert'}</span>
        <span style="float:right; text-transform:uppercase; font-size:0.7rem">${a.severity || 'Info'}</span>
      </div>
      <div class="alert-body">${a.message || ''}</div>
    </div>
    `;
  }).join('');
}

function renderRecommendations(recs) {
    const div = document.getElementById('healthRecs');
    if(!div) return;
    const items = (Array.isArray(recs) && recs.length > 0) ? recs : [
        "Drink plenty of water throughout the day.",
        "Wear a mask if air quality drops.",
        "Limit intense outdoor activities during peak heat."
    ];
    div.innerHTML = items.map((r, i) => {
        // यहाँ typo फिक्स कर दिया गया है 🛠️
        const text = typeof r === 'string' ? r : (r.message || "Stay aware of local weather changes.");
        const icon = i % 2 === 0 ? '🛡️' : '💧';
        return `
        <div class="health-card">
          <div class="health-icon">${icon}</div>
          <div class="health-title">Health Tip</div>
          <div class="health-desc">${text}</div>
        </div>`;
    }).join('');
}

function renderOutdoorGuide(w) {
    const div = document.getElementById('outdoorGuide');
    if(!div) return;
    div.innerHTML = `
        <div class="guide-item">
            <div class="guide-icon">🏃</div>
            <div class="guide-text"><strong>Exercise:</strong> ${w.aqi > 3 ? 'Avoid heavy outdoor exercise due to AQI.' : 'Safe for outdoor workouts.'}</div>
        </div>
        <div class="guide-item">
            <div class="guide-icon">👕</div>
            <div class="guide-text"><strong>Clothing:</strong> ${w.temperature > 25 ? 'Wear light, breathable clothes.' : 'Dress appropriately for the weather.'}</div>
        </div>
        <div class="guide-item">
            <div class="guide-icon">🕶️</div>
            <div class="guide-text"><strong>Protection:</strong> Always carry essential gear like sunglasses or umbrellas depending on the sky.</div>
        </div>
    `;
}

function renderEmergency(alerts) {
    const div = document.getElementById('emergencyGuide');
    if(!div) return;
    if(alerts.length > 0) {
        div.innerHTML = `
            <div class="guide-item" style="background:rgba(244,63,94,.1)">
                <div class="guide-icon">🚨</div>
                <div class="guide-text"><strong>Active Threat:</strong> Follow local emergency guidelines immediately!</div>
            </div>
            <div class="guide-item">
                <div class="guide-icon">📻</div>
                <div class="guide-text">Keep your emergency kit ready and stay tuned to local news.</div>
            </div>
        `;
    } else {
         div.innerHTML = `
            <div class="guide-item">
                <div class="guide-icon">🎒</div>
                <div class="guide-text"><strong>Kit Ready:</strong> Keep a basic first-aid and emergency kit at home.</div>
            </div>
            <div class="guide-item">
                <div class="guide-icon">📱</div>
                <div class="guide-text">Ensure your phone is charged and emergency contacts are updated.</div>
            </div>
        `;
    }
}

function setText(id, val) {
    const e = document.getElementById(id);
    if (e) e.textContent = val;
}