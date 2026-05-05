/**
 * WeatherIQ Route Planner — v7 (Voice Enabled)
 * Uses ORS real routing. Origin auto-populated from global location.
 */
'use strict';

// ─── Auto-populate origin from global location ────────────────────────────────
window.addEventListener('wiq:location', () => {
  const originInput = document.getElementById('originInput');
  if (originInput && !originInput._userModified) {
    originInput.value = window.WIQ.displayName || window.WIQ.city || '';
  }
});

document.addEventListener('DOMContentLoaded', () => {
  const originInput = document.getElementById('originInput');
  if (originInput) {
    originInput.value = window.WIQ.displayName || window.WIQ.city || 'Delhi';
    originInput.addEventListener('input', () => { originInput._userModified = true; });
  }
  document.getElementById('routeForm')?.addEventListener('submit', handleRouteSubmit);
});

async function handleRouteSubmit(e) {
  e.preventDefault();
  const origin = document.getElementById('originInput')?.value.trim();
  const dest   = document.getElementById('destInput')?.value.trim();
  if (!origin || !dest) { showToast('Enter both origin and destination', 'error'); return; }

  setLoader(true, `Planning route: ${origin} → ${dest}…`);
  document.getElementById('routeResult')?.classList.add('hidden');

  try {
    const r = await fetch(`/api/intelligence/route?origin=${encodeURIComponent(origin)}&dest=${encodeURIComponent(dest)}`);
    const d = await r.json();
    if (!d.success) throw new Error(d.error || 'Route failed');
    
    renderRoute(d.data);

    // 🔥 NAYA: Voice summary after rendering
    setTimeout(() => {
        speakRoutePlanner(d.data);
    }, 1500);

  } catch (err) {
    showToast(`Route error: ${err.message}`, 'error');
    console.error(err);
  } finally {
    setLoader(false);
  }
}

function renderRoute(data) {
  const container = document.getElementById('routeResult');
  if (!container) return;

  const srcBadge = data.route_source === 'ors_real'
    ? '<span class="badge badge-success">🗺️ Real Roads (ORS)</span>'
    : '<span class="badge badge-warning">📐 Estimated Route</span>';

  container.innerHTML = `
    <div class="route-header">
      <div class="route-summary">
        <h3>🗺️ ${data.origin} → ${data.destination}</h3>
        <div class="route-meta">
          ${srcBadge}
          <span class="badge" style="background:${data.risk_color}20;color:${data.risk_color};border-color:${data.risk_color}40">${data.risk_label}</span>
        </div>
      </div>
      <div class="route-stats-grid">
        <div class="route-stat"><span class="route-stat-val">${data.distance_km} km</span><span class="route-stat-lbl">Distance</span></div>
        <div class="route-stat"><span class="route-stat-val">${data.eta_hours}h</span><span class="route-stat-lbl">ETA</span></div>
        <div class="route-stat"><span class="route-stat-val">${data.avg_speed_kmh} km/h</span><span class="route-stat-lbl">Avg Speed</span></div>
        <div class="route-stat"><span class="route-stat-val" style="color:${data.weather_delay_hr > 0 ? '#f97316':'#10b981'}">+${data.weather_delay_hr}h</span><span class="route-stat-lbl">Weather Delay</span></div>
      </div>
    </div>

    <div class="recommendation-box" style="border-left:3px solid ${data.risk_color}">
      ${data.recommendation}
    </div>

    <div class="route-waypoints">
      <h4 style="margin-bottom:12px;font-size:.85rem;color:var(--text-2)">WEATHER ALONG ROUTE</h4>
      <div class="waypoints-grid">
        ${data.segments.map(seg => `
          <div class="waypoint-card" style="border-top:2px solid ${seg.risk_color}">
            <div class="wp-label">${seg.label}</div>
            <div class="wp-distance">${seg.distance_km} km from origin</div>
            <div class="wp-weather">
              <span>${getWeatherEmoji(seg.weather_main)}</span>
              <span>${seg.temperature !== '--' ? Math.round(seg.temperature) + '°C' : '--'}</span>
            </div>
            <div class="wp-details">
              <span>💧 ${seg.humidity !== '--' ? seg.humidity + '%' : '--'}</span>
              <span>💨 ${seg.wind_speed !== '--' ? seg.wind_speed + ' km/h' : '--'}</span>
              <span>🌧️ ${seg.rain_1h ?? 0} mm</span>
            </div>
            <div class="wp-risk-bar">
              <div style="width:${seg.risk}%;background:${seg.risk_color};height:4px;border-radius:2px;transition:width .5s"></div>
            </div>
            <div style="font-size:.7rem;color:${seg.risk_color};font-weight:600">${seg.risk_label}</div>
          </div>
        `).join('')}
      </div>
    </div>

    <div class="transport-modes">
      <h4 style="margin-bottom:10px;font-size:.85rem;color:var(--text-2)">TRANSPORT RECOMMENDATION</h4>
      <div style="display:flex;flex-wrap:wrap;gap:8px">
        ${data.transport_modes.map(m => `
          <div class="transport-mode ${m.recommended ? 'recommended' : 'not-recommended'}">
            <span>${m.mode}</span>
            <span style="font-size:.7rem;color:var(--text-2)">${m.note}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
  container.classList.remove('hidden');
  container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ─── 🗣️ ROUTE PLANNER VOICE ENGINE (ZIDDI HINDI) ───────────────────────────
function speakRoutePlanner(data) {
    if (!data) return;
    window.speechSynthesis.cancel(); 

    let script = `${data.origin} से ${data.destination} तक का सफर प्लान किया गया है। `;
    script += `सफर की कुल दूरी ${data.distance_km} किलोमीटर है। `;
    script += `रास्ते में मौसम के कारण लगभग ${data.weather_delay_hr} घंटे की देरी हो सकती है। `;
    
    script += `अभी सुरक्षा का स्तर ${data.risk_label} है। `;
    
    if (data.recommendation) {
        script += `सफर के लिए मुख्य सलाह यह है कि: ${data.recommendation}। `;
    }

    script += "अपनी यात्रा सुरक्षित रखें। धन्यवाद।";

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

function getWeatherEmoji(main) {
  const map = { Clear:'☀️', Clouds:'☁️', Rain:'🌧️', Drizzle:'🌦️',
                Thunderstorm:'⛈️', Mist:'🌫️', Fog:'🌫️', Snow:'❄️' };
  return map[main] || '🌡️';
}