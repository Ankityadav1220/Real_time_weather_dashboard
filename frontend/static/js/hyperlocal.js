/**
 * WeatherIQ Hyperlocal — v6
 * Uses GPS coordinates automatically from global location state.
 */
'use strict';

window.addEventListener('wiq:location', (e) => {
  if (e.detail.lat != null && e.detail.lon != null) loadHyperlocal(e.detail.lat, e.detail.lon);
});

document.addEventListener('DOMContentLoaded', () => {
  const loc = window.WIQ;
  if (loc.lat != null && loc.lon != null) {
    loadHyperlocal(loc.lat, loc.lon);
  } else {
    const statusEl = document.getElementById('hyperlocalStatus');
    if (statusEl) statusEl.textContent = 'Click 📍 in the top bar to use your GPS location';
  }

  document.getElementById('gpsBtnHyper')?.addEventListener('click', () => {
    navigator.geolocation?.getCurrentPosition(pos => {
      window.setLocation({
        lat: pos.coords.latitude, lon: pos.coords.longitude,
        city: window.WIQ.city, displayName: window.WIQ.displayName
      });
    }, () => showToast('GPS unavailable', 'error'));
  });
});

async function loadHyperlocal(lat, lon) {
  const loading = document.getElementById('hyperlocalLoading');
  const content = document.getElementById('hyperlocalContent');
  if (loading) loading.classList.remove('hidden');
  if (content) content.classList.add('hidden');
  try {
    const r = await fetch(`/api/intelligence/hyperlocal?lat=${lat}&lon=${lon}`);
    const d = await r.json();
    if (d.success && d.data) renderHyperlocal(d.data, lat, lon);
  } catch(e) {
    showToast('Hyperlocal fetch failed', 'error');
  } finally {
    if (loading) loading.classList.add('hidden');
    if (content) content.classList.remove('hidden');
  }
}

function renderHyperlocal(data, lat, lon) {
  const hl = data.hyperlocal || {};
  setText('hlCity',     data.city || window.WIQ.displayName || '--');
  setText('hlCoords',   `${lat.toFixed(4)}°, ${lon.toFixed(4)}°`);
  setText('hlTemp',     `${hl.adjusted_temp ?? data.temperature ?? '--'}°C`);
  setText('hlHumidity', `${hl.adjusted_humidity ?? data.humidity ?? '--'}%`);
  setText('hlUHI',      `+${hl.urban_heat_island ?? 0}°C`);
  setText('hlZone',     hl.micro_zone || '--');
  setText('hlConfidence',`${hl.confidence_pct ?? '--'}%`);
  setText('hlRadius',   `${hl.radius_km ?? '--'} km`);
  setText('hlWeather',  `${data.weather_main || '--'} — ${data.weather_description || ''}`);
  setText('hlWind',     `${data.wind_speed ?? '--'} km/h`);
  setText('hlPressure', `${data.pressure ?? '--'} hPa`);
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
