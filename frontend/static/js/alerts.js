'use strict';
window.addEventListener('wiq:location', loadAlertsAndSafety);
document.addEventListener('DOMContentLoaded', loadAlertsAndSafety);

// HTML के 🔄 Refresh बटन को चालू करने के लिए
window.refreshAlerts = loadAlertsAndSafety;

async function loadAlertsAndSafety() {
  const params = window.locationParams ? window.locationParams() : 'city=Delhi';

  try {
    // Current-weather API में Alerts और AQI दोनों का डेटा एक साथ मिल जाता है
    const r = await fetch(`/api/current-weather?${params}`);
    const d = await r.json();

    if (d.success && d.data) {
        const w = d.data;

        // 1. सबसे ऊपर वाले 5 छोटे कार्ड्स अपडेट करें (Summary Row)
        const alertCount = w.alerts ? w.alerts.length : 0;
        setText('al-total', alertCount);
        setText('al-aqi', w.aqi || '--');
        setText('al-uv', w.uv_index !== undefined ? w.uv_index : '--');
        setText('al-heat', w.feels_like !== undefined ? `${Math.round(w.feels_like)}°C` : '--°C');
        setText('al-dew', w.dew_point !== undefined ? `${Math.round(w.dew_point)}°C` : '--°C');

        // 2. Active Alerts लिस्ट अपडेट करें
        renderAlerts(w.alerts || []);

        // 3. बीच वाले बड़े एयर क्वालिटी (AQI) कार्ड को अपडेट करें
        setText('aqiBig', w.aqi || '--');
        if (w.aqi_info) {
            setText('aqiBigLbl', w.aqi_info.label || 'Unknown');
            
            // AQI का कलर बार (Gauge Fill)
            const aqiColor = w.aqi_info.color || 'var(--success)';
            const gauge = document.getElementById('aqiGaugeFill');
            if (gauge) {
                gauge.style.background = aqiColor;
                // मान लेते हैं AQI स्केल 5 तक है (1-5)
                gauge.style.width = Math.min((w.aqi / 5) * 100, 100) + '%';
            }
        }

        // 4. हीट और UV इंडेक्स वाला कार्ड अपडेट करें
        setText('heatIndexVal', w.feels_like !== undefined ? `${Math.round(w.feels_like)}°C` : '--°C');
        setText('uvVal', w.uv_index !== undefined ? w.uv_index : '--');
        setText('dewPointVal', w.dew_point !== undefined ? `${Math.round(w.dew_point)}°C` : '--°C');
        setText('uvDesc', w.uv_advice || 'Stay safe and monitor local conditions.');
    }
  } catch (e) {
      console.error('Failed to fetch safety cards data:', e);
  }
}

function renderAlerts(alerts) {
  // HTML में अलर्ट्स वाले बॉक्स की ID 'activeAlerts' है
  const list = document.getElementById('activeAlerts'); 
  if (!list) return;

  if (!alerts || alerts.length === 0) {
    list.innerHTML = `<div style="color:var(--success);font-size:.88rem;padding:12px">✅ No active weather alerts for this city</div>`;
    return;
  }

  list.innerHTML = alerts.map(a => {
    // अलर्ट की सीरियसनेस के हिसाब से CSS क्लास (कलर) तय करना
    let sevClass = 'info';
    const s = (a.severity || '').toLowerCase();
    if (s.includes('high') || s.includes('extreme') || s.includes('severe')) sevClass = 'danger';
    else if (s.includes('mod') || s.includes('warn')) sevClass = 'warning';
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

function setText(id, val) {
    const e = document.getElementById(id);
    if (e) e.textContent = val;
}