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

        // --- 1. LIVE Top Stats ---
        const alertCount = w.alerts ? w.alerts.length : 0;
        setText('al-total', alertCount);
        setText('al-aqi', w.aqi || '--');

        // Live UV 
        const uv = w.uv_index !== undefined ? w.uv_index : (w.uvi !== undefined ? w.uvi : '--');
        setText('al-uv', uv);

        // Live Dew Point (Calculated accurately from Live Temp & Humidity)
        let dew = w.dew_point;
        if (dew === undefined && w.temperature !== undefined && w.humidity !== undefined) {
            dew = w.temperature - ((100 - w.humidity) / 5);
        }
        const dewStr = dew !== undefined ? `${Math.round(dew)}°C` : '--°C';

        // Live Heat Index (Feels Like)
        setText('al-heat', w.feels_like !== undefined ? `${Math.round(w.feels_like)}°C` : '--°C');
        setText('al-dew', dewStr);

        // --- 2. LIVE Active Alerts ---
        renderAlerts(w.alerts || []);

        // --- 3. LIVE Air Quality Details ---
        setText('aqiBig', w.aqi || '--');
        if (w.aqi_info) {
            setText('aqiBigLbl', w.aqi_info.label || 'Unknown');
            const gauge = document.getElementById('aqiGaugeFill');
            if (gauge) {
                gauge.style.background = w.aqi_info.color || 'var(--success)';
                gauge.style.width = Math.min(((w.aqi || 1) / 5) * 100, 100) + '%';
            }
        }
        setText('aqiBigDesc', 'Real-time air pollution metrics from live weather station.');

        // 🔥 STRICTLY LIVE GAS DATA (No fake multiplication)
        // Agar backend se data aayega tabhi dikhega, warna '--' dikhega
        setText('pm25', w.components && w.components.pm2_5 !== undefined ? w.components.pm2_5.toFixed(1) : '--');
        setText('pm10', w.components && w.components.pm10 !== undefined ? w.components.pm10.toFixed(1) : '--');
        setText('co2',  w.components && w.components.co !== undefined ? w.components.co.toFixed(1) : '--');
        setText('o3',   w.components && w.components.o3 !== undefined ? w.components.o3.toFixed(1) : '--');

        // --- 4. LIVE Heat & UV Safety ---
        setText('heatIndexVal', w.feels_like !== undefined ? `${Math.round(w.feels_like)}°C` : '--°C');
        setText('uvVal', uv);
        setText('dewPointVal', dewStr);

        setText('heatIndexDesc', w.feels_like > 35 ? 'High heat danger. Stay hydrated.' : 'Comfortable temperature range.');
        setText('uvDesc', w.uv_advice || (uv > 5 ? 'High UV risk. Wear sunscreen.' : 'Low UV risk today.'));
        setText('dewDesc', dew > 20 ? 'Very humid and muggy.' : 'Comfortable humidity levels.');

        // --- 5. LIVE Recommendations based on current weather ---
        renderRecommendations(w.activity_recommendations || [], w);
        renderOutdoorGuide(w);
        renderEmergency(w.alerts || []);
    }
  } catch (e) {
      console.error('Failed to fetch live safety data:', e);
  }
}

function renderAlerts(alerts) {
  const list = document.getElementById('activeAlerts');
  if (!list) return;
  if (!alerts || alerts.length === 0) {
    list.innerHTML = `<div style="color:var(--success);font-size:.88rem;padding:12px">✅ All clear! No active weather threats.</div>`;
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

function renderRecommendations(recs, w) {
    const div = document.getElementById('healthRecs');
    if(!div) return;
    
    // Default live recs based on LIVE AQI/Temp if API doesn't send specific array
    let items = (Array.isArray(recs) && recs.length > 0) ? recs : [];
    if (items.length === 0) {
        if (w.aqi > 3) items.push("Air Quality is poor. Wear an N95 mask outdoors.");
        if (w.feels_like > 35) items.push("Extreme heat detected. Stay indoors and hydrate.");
        if (w.humidity > 80) items.push("High humidity. Use dehumidifiers if prone to allergies.");
        if (items.length === 0) items.push("Conditions are currently safe for regular activities.");
    }

    div.innerHTML = items.map((r, i) => {
        const text = typeof r === 'string' ? r : (r.message || "Stay aware of local weather changes.");
        const icon = text.toLowerCase().includes('mask') || text.toLowerCase().includes('air') ? '😷' : 
                     text.toLowerCase().includes('heat') || text.toLowerCase().includes('water') ? '💧' : '🛡️';
        return `
        <div class="health-card">
          <div class="health-icon">${icon}</div>
          <div class="health-title">Live Health Tip</div>
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
            <div class="guide-text"><strong>Exercise:</strong> ${w.aqi > 3 ? 'Avoid heavy outdoor exercise due to current AQI.' : 'Safe for outdoor workouts.'}</div>
        </div>
        <div class="guide-item">
            <div class="guide-icon">👕</div>
            <div class="guide-text"><strong>Clothing:</strong> ${(w.feels_like || w.temperature) > 28 ? 'Wear light, breathable cotton clothes.' : 'Dress comfortably for current conditions.'}</div>
        </div>
        <div class="guide-item">
            <div class="guide-icon">🕶️</div>
            <div class="guide-text"><strong>Protection:</strong> ${w.uv_index > 5 ? 'High UV today! Wear sunglasses and SPF 50+ sunscreen.' : 'Normal protection required today.'}</div>
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