/**
 * WeatherIQ Dashboard — v8 (Full Voice Summary + Data Fix)
 */
'use strict';

let tempChart = null;
let _dashInit = false;

window.addEventListener('wiq:location', () => { loadDashboard(); });

async function loadDashboard() {
  try {
    const params = window.locationParams();
    const [wRes, fcRes, alertRes] = await Promise.all([
      fetch(`/api/current-weather?${params}`),
      fetch(`/api/forecast?${params}`),
      fetch(`/api/alerts?${params}`)
    ]);
    const [wData, fcData, alertData] = await Promise.all([
      wRes.json(), fcRes.json(), alertRes.json()
    ]);

    if (wData.success && wData.data) {
        renderWeather(wData.data);
        // Poori details bolne ke liye 1.5s ka delay
        setTimeout(() => {
            speakFullDashboardSummary(wData.data);
        }, 1500);
    }
    if (fcData.success && fcData.data) renderForecastChart(fcData.data);
    if (alertData.success || alertData.data) renderAlerts(alertData.data || alertData.alerts || []);
  } catch (e) {
    console.error('[Dashboard] load error:', e);
  }
}

function renderWeather(w) {
  applyWeatherBackground(w.weather_main);

  // Big Display
  setText('tempBig', w.temperature != null ? Math.round(w.temperature) : '--');
  setText('feelsLike', `Feels like ${w.feels_like ?? '--'}°C`);
  setText('wDesc', w.weather_description || w.weather_main || '--');
  setText('cityCountry', `${w.city || ''}, ${w.country || ''}`);

  // FIX: Dash-Dash areas (Checking keys properly)
  setText('tMax', w.temp_max || w.main?.temp_max || '--');
  setText('tMin', w.temp_min || w.main?.temp_min || '--');
  setText('sunrise', w.sunrise || '--');
  setText('sunset', w.sunset || '--');

  // Top Stats
  setText('s-temp', `${Math.round(w.temperature ?? 0)}°`);
  setText('s-hum',  `${w.humidity ?? '--'}%`);
  setText('s-wind', `${w.wind_speed ?? '--'}`);
  setText('s-aqi',  (w.aqi_info?.label) || '--');
  setText('s-vis',  w.visibility ? `${(w.visibility/1000).toFixed(1)}` : '--');

  // Bottom Grid
  setText('m-hum',   `${w.humidity ?? '--'}%`);
  setText('m-wind',  `${w.wind_speed ?? '--'} km/h`);
  setText('m-pres',  `${w.pressure ?? '--'}`);
  setText('m-vis',   w.visibility ? `${(w.visibility/1000).toFixed(1)} km` : '--');
  setText('m-cloud', `${w.cloud_coverage ?? '--'}%`);
  setText('m-rain',  `${w.rain_1h ?? 0} mm`);

  setText('wIcon', getWeatherEmoji(w.weather_main));

  const aqi = w.aqi_info;
  if (aqi) {
    const num = document.getElementById('aqiNum');
    const lbl = document.getElementById('aqiLbl');
    const circle = document.getElementById('aqiCircle');
    const desc = document.getElementById('aqiDesc');
    if (num) { num.textContent = aqi.value; num.style.color = aqi.color; }
    if (lbl) lbl.textContent = aqi.label;
    if (circle) circle.style.borderColor = aqi.color;
    if (desc) desc.textContent = aqiDesc(aqi.value);
  }
}

// ─── 🗣️ POORI DETAILS BOLNE WALA ENGINE ──────────────────────────────────────
function speakFullDashboardSummary(w) {
  if (!w) return;
  window.speechSynthesis.cancel();

  const city = w.city || 'शहर';
  const temp = Math.round(w.temperature);
  const desc = w.weather_description || 'साफ';
  const wind = w.wind_speed || '0';
  const humidity = w.humidity || '0';
  const visibility = w.visibility ? (w.visibility / 1000).toFixed(1) : '0';
  const aqi = (w.aqi_info && w.aqi_info.label) || 'सामान्य';

  // Poori Script jisme saari details hain
  const script = `${city} का मौसम हाल। अभी तापमान ${temp} डिग्री है और बाहर ${desc} है। हवा की रफ्तार ${wind} किलोमीटर प्रति घंटा है और नमी ${humidity} प्रतिशत है। दृश्यता ${visibility} किलोमीटर है और हवा की गुणवत्ता ${aqi} है। सुरक्षित रहें।`;

  const forceSpeak = () => {
    const voices = window.speechSynthesis.getVoices();
    const hindi = voices.find(v => v.lang.includes('hi') || v.name.toLowerCase().includes('hindi'));

    if (!hindi && voices.length > 0) {
      setTimeout(forceSpeak, 250);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(script);
    utterance.lang = 'hi-IN';
    utterance.rate = 0.85; // Thoda slow taaki sab samajh aaye
    if (hindi) utterance.voice = hindi;

    window.speechSynthesis.speak(utterance);
  };

  if (window.speechSynthesis.getVoices().length === 0) {
    window.speechSynthesis.onvoiceschanged = forceSpeak;
  } else {
    forceSpeak();
  }
}

// ─── HELPERS ───
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function getWeatherEmoji(main) {
  const map = { Clear:'☀️', Clouds:'☁️', Rain:'🌧️', Haze:'🌫️', Mist:'🌫️', Thunderstorm:'⛈️' };
  return map[main] || '🌡️';
}

function aqiDesc(v) {
  const d = { 1: 'Excellent', 2: 'Fair', 3: 'Moderate', 4: 'Poor', 5: 'Very Poor' };
  return d[v] || 'Monitoring...';
}

// Rest of your functions (Charts/Alerts) go here...
document.addEventListener('DOMContentLoaded', () => { loadDashboard(); });