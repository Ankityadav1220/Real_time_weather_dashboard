/**
 * WeatherIQ AI — Base JavaScript v6
 * Global Location State Management (Single Source of Truth)
 * All modules listen to 'wiq:location' event and auto-refresh.
 */
'use strict';

// ═══════════════════════════════════════════════════════════════════════════
// GLOBAL LOCATION STATE (window.WIQ)
// ═══════════════════════════════════════════════════════════════════════════
window.WIQ = window.WIQ || {
  city: null,
  lat:  null,
  lon:  null,
  displayName: null,  // e.g. "Satrikh, Uttar Pradesh"
  _listeners: [],
};

const LS_KEY = 'wiq_location_v2';

/** Load persisted location from localStorage */
function _loadPersistedLocation() {
  try {
    const saved = localStorage.getItem(LS_KEY);
    if (saved) {
      const loc = JSON.parse(saved);
      if (loc && loc.city) {
        window.WIQ.city        = loc.city;
        window.WIQ.lat         = loc.lat  || null;
        window.WIQ.lon         = loc.lon  || null;
        window.WIQ.displayName = loc.displayName || loc.city;
      }
    }
  } catch(e) {}
  if (!window.WIQ.city) {
    window.WIQ.city        = 'Delhi';
    window.WIQ.displayName = 'Delhi';
  }
}

/** Persist current location to localStorage */
function _persistLocation() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify({
      city:        window.WIQ.city,
      lat:         window.WIQ.lat,
      lon:         window.WIQ.lon,
      displayName: window.WIQ.displayName,
    }));
  } catch(e) {}
}

/**
 * setLocation — THE single function to update global location.
 * Fires 'wiq:location' event → all modules refresh automatically.
 */
window.setLocation = function(opts) {
  // opts: { city, lat, lon, displayName }
  const prev = window.WIQ.city;
  if (opts.city)        window.WIQ.city        = opts.city;
  if (opts.lat != null) window.WIQ.lat         = opts.lat;
  if (opts.lon != null) window.WIQ.lon         = opts.lon;
  window.WIQ.displayName = opts.displayName || opts.city || window.WIQ.city;

  _persistLocation();

  // Update search bar
  const input = document.getElementById('globalSearch');
  if (input) input.value = window.WIQ.displayName;

  // Update topbar location pill
  const pill = document.getElementById('locationPill');
  if (pill) pill.textContent = '📍 ' + window.WIQ.displayName;

  // Fire global event — all modules listen to this
  const evt = new CustomEvent('wiq:location', {
    detail: {
      city:        window.WIQ.city,
      lat:         window.WIQ.lat,
      lon:         window.WIQ.lon,
      displayName: window.WIQ.displayName,
      changed:     prev !== window.WIQ.city,
    }
  });
  window.dispatchEvent(evt);

  if (prev !== window.WIQ.city) {
    showToast(`📍 Location: ${window.WIQ.displayName}`, 'success');
    applyWeatherBackground('Clear');  // reset bg until weather loads
  }
};

/** Get current location state */
window.getLocation = function() {
  return {
    city:        window.WIQ.city,
    lat:         window.WIQ.lat,
    lon:         window.WIQ.lon,
    displayName: window.WIQ.displayName,
  };
};

/** Build API query string for current location (lat/lon preferred, city fallback) */
window.locationParams = function(extra) {
  const loc = window.WIQ;
  let params = '';
  if (loc.lat != null && loc.lon != null) {
    params = `lat=${loc.lat}&lon=${loc.lon}&city=${encodeURIComponent(loc.city || '')}`;
  } else {
    params = `city=${encodeURIComponent(loc.city || 'Delhi')}`;
  }
  if (extra) params += '&' + extra;
  return params;
};

// ═══════════════════════════════════════════════════════════════════════════
// THEME
// ═══════════════════════════════════════════════════════════════════════════
function getTheme() { return localStorage.getItem('wiq_theme') || 'dark'; }
function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = t === 'dark' ? '🌙' : '☀️';
  localStorage.setItem('wiq_theme', t);
}
function toggleTheme() { applyTheme(getTheme() === 'dark' ? 'light' : 'dark'); }
window.toggleTheme = toggleTheme;

// ═══════════════════════════════════════════════════════════════════════════
// SIDEBAR
// ═══════════════════════════════════════════════════════════════════════════
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const mc = document.getElementById('mainContent');
  if (!sb) return;
  if (window.innerWidth > 900) {
    sb.classList.toggle('collapsed');
    const c = sb.classList.contains('collapsed');
    if (mc) mc.classList.toggle('full', c);
    document.getElementById('topbar')?.classList.toggle('full', c);
  } else {
    sb.classList.toggle('open');
    document.getElementById('sidebarOverlay')?.classList.toggle('visible',
      sb.classList.contains('open'));
  }
}
window.toggleSidebar = toggleSidebar;

// ═══════════════════════════════════════════════════════════════════════════
// CLOCK
// ═══════════════════════════════════════════════════════════════════════════
function startClock() {
  const el = document.getElementById('liveClock');
  if (!el) return;
  const tick = () => el.textContent = new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
  tick();
  setInterval(tick, 1000);
}

// ═══════════════════════════════════════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════════════════════════════════════
function showToast(msg, type = 'info', ms = 3500) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className = `toast ${type}`;
  el.classList.remove('hidden');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add('hidden'), ms);
}
window.showToast = showToast;

// ═══════════════════════════════════════════════════════════════════════════
// LOADER
// ═══════════════════════════════════════════════════════════════════════════
function setLoader(show, text = 'Loading…') {
  const el = document.getElementById('pageLoader');
  if (!el) return;
  el.classList.toggle('hidden', !show);
  const lt = document.getElementById('loaderText');
  if (lt) lt.textContent = text;
}
window.setLoader = setLoader;

// ═══════════════════════════════════════════════════════════════════════════
// GPS GEOLOCATION
// ═══════════════════════════════════════════════════════════════════════════
function requestGeolocation(silent = false) {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const { latitude: lat, longitude: lon } = pos.coords;
      try {
        const r = await fetch(`/api/geo-weather?lat=${lat}&lon=${lon}`);
        const d = await r.json();
        if (d.success) {
          window.setLocation({
            city:        d.city,
            lat:         lat,
            lon:         lon,
            displayName: d.city,
          });
          if (d.data?.weather_main) applyWeatherBackground(d.data.weather_main);
          if (!silent) showToast(`📍 Location: ${d.city}`, 'success');
        }
      } catch (e) {
        if (!silent) showToast('Could not detect location', 'error');
      }
    },
    () => { if (!silent) showToast('Location permission denied', 'error'); },
    { timeout: 8000, maximumAge: 300000 }
  );
}

function setupGeolocationButton() {
  const btn = document.getElementById('geoBtn');
  if (!btn) return;
  btn.addEventListener('click', () => {
    btn.textContent = '⏳';
    navigator.geolocation?.getCurrentPosition(
      async (pos) => {
        const { latitude: lat, longitude: lon } = pos.coords;
        try {
          const r = await fetch(`/api/geo-weather?lat=${lat}&lon=${lon}`);
          const d = await r.json();
          if (d.success) {
            window.setLocation({ city: d.city, lat, lon, displayName: d.city });
            if (d.data?.weather_main) applyWeatherBackground(d.data.weather_main);
          }
        } catch (e) { showToast('Location error', 'error'); }
        btn.textContent = '📍';
      },
      () => { showToast('Permission denied', 'error'); btn.textContent = '📍'; },
      { timeout: 8000 }
    );
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// AUTOCOMPLETE SEARCH
// ═══════════════════════════════════════════════════════════════════════════
function setupAutocomplete() {
  const input = document.getElementById('globalSearch');
  const list  = document.getElementById('autocompleteList');
  if (!input || !list) return;

  // Set initial value
  input.value = window.WIQ.displayName || window.WIQ.city || '';

  let timer;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 1) { list.classList.remove('open'); return; }
    timer = setTimeout(async () => {
      try {
        const r = await fetch(`/api/autocomplete?q=${encodeURIComponent(q)}`);
        const cities = await r.json();
        list.innerHTML = cities.map(c =>
          `<div class="ac-item" data-city="${c}">${c}</div>`
        ).join('');
        list.classList.toggle('open', cities.length > 0);
        list.querySelectorAll('.ac-item').forEach(el => {
          el.addEventListener('click', () => {
            const city = el.dataset.city;
            input.value = city;
            list.classList.remove('open');
            // City search: no lat/lon, backend will resolve
            window.setLocation({ city, displayName: city, lat: null, lon: null });
          });
        });
      } catch (_) { list.classList.remove('open'); }
    }, 200);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = input.value.trim();
      list.classList.remove('open');
      if (q) window.setLocation({ city: q, displayName: q, lat: null, lon: null });
    }
    if (e.key === 'Escape') list.classList.remove('open');
  });

  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !list.contains(e.target)) {
      list.classList.remove('open');
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// WEATHER BACKGROUND ANIMATIONS
// ═══════════════════════════════════════════════════════════════════════════
const WEATHER_CLASSES = ['weather-clear','weather-rain','weather-cloudy',
                         'weather-storm','weather-fog','weather-snow'];

function applyWeatherBackground(weatherMain) {
  const body = document.body;
  const bg   = document.getElementById('weatherBg');
  WEATHER_CLASSES.forEach(c => body.classList.remove(c));

  let cls = 'weather-clear';
  switch ((weatherMain || '').toLowerCase()) {
    case 'rain': case 'drizzle':       cls = 'weather-rain';   break;
    case 'thunderstorm':               cls = 'weather-storm';  break;
    case 'clouds':                     cls = 'weather-cloudy'; break;
    case 'mist': case 'fog':
    case 'haze': case 'smoke':         cls = 'weather-fog';    break;
    case 'snow':                       cls = 'weather-snow';   break;
    default:                           cls = 'weather-clear';  break;
  }
  body.classList.add(cls);
  if (bg) bg.setAttribute('data-weather', cls);

  // Dynamic particles
  createWeatherParticles(cls);
}
window.applyWeatherBackground = applyWeatherBackground;

function createWeatherParticles(cls) {
  const container = document.getElementById('weatherParticles');
  if (!container) return;
  container.innerHTML = '';

  if (cls === 'weather-rain') {
    for (let i = 0; i < 60; i++) {
      const drop = document.createElement('div');
      drop.className = 'rain-drop';
      drop.style.cssText = `
        left: ${Math.random()*100}%;
        animation-delay: ${Math.random()*2}s;
        animation-duration: ${0.6 + Math.random()*0.6}s;
        opacity: ${0.4 + Math.random()*0.5};
      `;
      container.appendChild(drop);
    }
  } else if (cls === 'weather-storm') {
    for (let i = 0; i < 80; i++) {
      const drop = document.createElement('div');
      drop.className = 'rain-drop storm-drop';
      drop.style.cssText = `
        left: ${Math.random()*100}%;
        animation-delay: ${Math.random()*1.5}s;
        animation-duration: ${0.4 + Math.random()*0.4}s;
      `;
      container.appendChild(drop);
    }
    // Lightning flash
    setInterval(() => {
      if (Math.random() > 0.7) {
        document.body.classList.add('lightning');
        setTimeout(() => document.body.classList.remove('lightning'), 200);
      }
    }, 3000);
  } else if (cls === 'weather-cloudy') {
    for (let i = 0; i < 5; i++) {
      const cloud = document.createElement('div');
      cloud.className = 'cloud-anim';
      cloud.style.cssText = `
        top: ${10 + Math.random()*30}%;
        animation-delay: ${-Math.random()*20}s;
        animation-duration: ${20 + Math.random()*20}s;
        transform: scale(${0.5 + Math.random()*0.8});
        opacity: ${0.15 + Math.random()*0.2};
      `;
      container.appendChild(cloud);
    }
  } else if (cls === 'weather-snow') {
    for (let i = 0; i < 50; i++) {
      const flake = document.createElement('div');
      flake.className = 'snow-flake';
      flake.textContent = '❄';
      flake.style.cssText = `
        left: ${Math.random()*100}%;
        font-size: ${8 + Math.random()*12}px;
        animation-delay: ${Math.random()*5}s;
        animation-duration: ${3 + Math.random()*4}s;
        opacity: ${0.4 + Math.random()*0.5};
      `;
      container.appendChild(flake);
    }
  } else if (cls === 'weather-fog') {
    for (let i = 0; i < 3; i++) {
      const fog = document.createElement('div');
      fog.className = 'fog-layer';
      fog.style.cssText = `
        top: ${20 + i*20}%;
        animation-delay: ${i*3}s;
        opacity: ${0.15 + i*0.05};
      `;
      container.appendChild(fog);
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// ALERT BADGE
// ═══════════════════════════════════════════════════════════════════════════
async function loadAlertBadge() {
  try {
    const loc = window.WIQ;
    const qs = loc.lat != null
      ? `lat=${loc.lat}&lon=${loc.lon}&city=${encodeURIComponent(loc.city||'')}`
      : `city=${encodeURIComponent(loc.city||'Delhi')}`;
    const r = await fetch(`/api/alerts?${qs}`);
    const d = await r.json();
    const count = (d.data || d.alerts || []).length;
    const badge = document.getElementById('alertBadge');
    if (badge) {
      badge.textContent = count;
      badge.style.display = count > 0 ? 'inline-flex' : 'none';
    }
  } catch (_) {}
}

// ═══════════════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  _loadPersistedLocation();
  applyTheme(getTheme());
  startClock();
  setupGeolocationButton();
  setupAutocomplete();

  // Set initial search bar value
  const input = document.getElementById('globalSearch');
  if (input) input.value = window.WIQ.displayName || window.WIQ.city || '';

  // Update location pill
  const pill = document.getElementById('locationPill');
  if (pill) pill.textContent = '📍 ' + (window.WIQ.displayName || window.WIQ.city || 'Delhi');

  // Load alert badge on location change
  window.addEventListener('wiq:location', () => {
    loadAlertBadge();
  });
  loadAlertBadge();

  // Mobile sidebar overlay close
  document.getElementById('sidebarOverlay')?.addEventListener('click', () => {
    document.getElementById('sidebar')?.classList.remove('open');
    document.getElementById('sidebarOverlay')?.classList.remove('visible');
  });

  // On first load, try silent geolocation (don't force)
  // requestGeolocation(true); // Uncomment to auto-detect on load

  console.log('[WeatherIQ] Global state ready:', window.WIQ);
});

// Expose legacy compat
window.getCurrentCity = function() { return window.WIQ.city || 'Delhi'; };
window.broadcastCityChange = function(city) {
  window.setLocation({ city, displayName: city, lat: null, lon: null });
};
