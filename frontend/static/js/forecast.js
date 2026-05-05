/**
 * WeatherIQ Forecast — v15 (Ultimate Error Catcher & Renderer)
 * Ab blank screen nahi aayegi, error directly screen par dikhega!
 */
'use strict';

let charts = {};
let currentForecastData = null; 
let currentCityName = null;

window.addEventListener('wiq:location', loadForecast);
document.addEventListener('DOMContentLoaded', loadForecast);

async function loadForecast() {
    try {
        // UI ko loading state mein daalo
        showLoadingState();

        const params = window.locationParams ? window.locationParams() : 'city=Delhi';
        
        // 🎯 Dono routes try karenge
        let r = await fetch(`/api/weather/forecast?${params}`);
        if (r.status === 404) {
            console.warn("/api/weather/forecast not found, trying /api/forecast...");
            r = await fetch(`/api/forecast?${params}`);
        }

        // 🎯 Text ke roop mein padho taaki HTML error bhi pakde ja sakein
        const dataText = await r.text();
        let d;
        try {
            d = JSON.parse(dataText);
        } catch (err) {
            throw new Error(`Server didn't return JSON. Route might be wrong. Status: ${r.status}`);
        }

        if (!r.ok || d.success === false) {
            throw new Error(d.error || d.message || `API Error: Status ${r.status}`);
        }

        const items = Array.isArray(d.data) ? d.data : (d.data?.list || d.list || []);
        if (items.length === 0) {
            throw new Error("Backend se data aaya, par forecast ki list khali hai (0 items).");
        }

        // Sab theek hai toh render karo
        currentForecastData = items;
        currentCityName = d.city;
        renderForecast(items, d.city);
        renderVoiceButton();

    } catch (e) {
        console.error('Forecast Load Error:', e);
        showErrorOnScreen(e.message);
    }
}

// 🎯 NAYA: ERROR KO SCREEN PAR DIKHANE WALA FUNCTION
function showErrorOnScreen(errorMessage) {
    // Stats ko Error mein badlo
    ['fc-high', 'fc-low', 'fc-rain', 'fc-wind', 'fc-hum'].forEach(id => {
        const el = document.getElementById(id);
        if(el) el.innerHTML = '<span style="color:#ef4444;font-size:0.9rem">Err</span>';
    });

    // Chart ke area mein lamba chouda error dikhao
    const chartArea = document.getElementById('fc-tempChart')?.parentElement;
    if (chartArea) {
        chartArea.innerHTML = `
            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; text-align:center; padding:20px;">
                <span style="font-size:3rem; margin-bottom:10px;">🚨</span>
                <h3 style="color:#ef4444; margin:0 0 10px 0;">Data Load Failed</h3>
                <p style="color:var(--text-2); font-family:monospace; background:rgba(239, 68, 68, 0.1); padding:10px; border-radius:5px; border:1px solid #ef4444; max-width:80%;">
                    ${errorMessage}
                </p>
                <p style="color:var(--text-3); font-size:0.8rem; margin-top:15px;">
                    Check your Python console to see if OpenWeather API is working.
                </p>
            </div>
        `;
    }
}

function showLoadingState() {
    setText('fc-high', '...'); setText('fc-low', '...');
    setText('fc-rain', '...'); setText('fc-wind', '...'); setText('fc-hum', '...');
}

// 🎯 Date Parser
function parseDate(f) {
    const val = f.dt_txt || f.forecast_time || f.dt;
    if (!val) return new Date();
    if (typeof val === 'number') return val < 10000000000 ? new Date(val * 1000) : new Date(val);
    return new Date(val);
}

function renderForecast(items, cityName) {
    setText('fcCity', cityName || window.WIQ?.displayName || "Delhi");

    const current = items[0];
    const temp = current.main?.temp ?? current.temperature ?? 0;
    const hi = current.main?.temp_max ?? current.temp_max ?? temp;
    const lo = current.main?.temp_min ?? current.temp_min ?? temp;
    
    let pop = current.pop ?? current.rain_probability ?? 0;
    if (pop > 0 && pop <= 1) pop = pop * 100;

    const wind = current.wind?.speed ?? current.wind_speed ?? 0;
    const hum = current.main?.humidity ?? current.humidity ?? 0;

    setText('fc-high', Math.round(hi) + '°C');
    setText('fc-low', Math.round(lo) + '°C');
    setText('fc-rain', Math.round(pop) + '%');
    setText('fc-wind', Math.round(wind) + ' km/h');
    setText('fc-hum', Math.round(hum) + '%');

    renderCharts(items);
    renderSevenDay(items);
    renderTable(items);
}

function renderCharts(items) {
    const hourly = items.slice(0, 24);
    const labels = hourly.map(h => parseDate(h).getHours() + ":00");
    const tc = document.documentElement.getAttribute('data-theme') === 'dark' ? '#94a3b8' : '#475569';
    const gc = document.documentElement.getAttribute('data-theme') === 'dark' ? 'rgba(255,255,255,.05)' : 'rgba(0,0,0,.05)';

    const tempCanvas = document.getElementById('fc-tempChart');
    if (tempCanvas) {
        if (charts.temp) charts.temp.destroy();
        charts.temp = new Chart(tempCanvas, {
            type: 'line',
            data: { labels, datasets: [{ label: 'Temp °C', data: hourly.map(h => h.main?.temp ?? h.temperature ?? 0), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', fill: true, tension: 0.4 }] },
            options: { responsive: true, maintainAspectRatio: false, scales: { x: { ticks: { color: tc }, grid: { display: false } }, y: { ticks: { color: tc }, grid: { color: gc } } }, plugins: { legend: { display: false } } }
        });
    }

    const rainCanvas = document.getElementById('fc-rainChart');
    if (rainCanvas) {
        if (charts.rain) charts.rain.destroy();
        charts.rain = new Chart(rainCanvas, {
            type: 'bar',
            data: { labels, datasets: [{ label: 'Rain %', data: hourly.map(h => { let p = h.pop ?? h.rain_probability ?? 0; return p <= 1 ? p * 100 : p; }), backgroundColor: '#3b82f6', borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, scales: { x: { ticks: { color: tc }, grid: { display: false } }, y: { min: 0, max: 100, ticks: { color: tc }, grid: { color: gc } } }, plugins: { legend: { display: false } } }
        });
    }

    const windCanvas = document.getElementById('fc-windpChart');
    if (windCanvas) {
        if (charts.wind) charts.wind.destroy();
        charts.wind = new Chart(windCanvas, {
            type: 'line',
            data: { labels, datasets: [{ label: 'Wind (km/h)', data: hourly.map(h => Math.round(h.wind?.speed ?? h.wind_speed ?? 0)), borderColor: '#10b981', tension: 0.4, yAxisID: 'y' }, { label: 'Pressure', data: hourly.map(h => h.main?.pressure ?? h.pressure ?? 1010), borderColor: '#8b5cf6', borderDash: [5, 5], tension: 0.4, yAxisID: 'y1' }] },
            options: { responsive: true, maintainAspectRatio: false, scales: { x: { ticks: { color: tc }, grid: { display: false } }, y: { position: 'left', ticks: { color: tc }, grid: { color: gc } }, y1: { position: 'right', ticks: { color: tc }, grid: { drawOnChartArea: false } } }, plugins: { legend: { display: false } } }
        });
    }
}

function renderSevenDay(items) {
    const container = document.getElementById('sevenDay');
    if (!container) return;
    const dayMap = {};
    items.forEach(item => { const d = parseDate(item).toLocaleDateString([], { weekday: 'short' }); if (!dayMap[d]) dayMap[d] = []; dayMap[d].push(item); });
    container.style.gridTemplateColumns = `repeat(${Math.min(7, Object.keys(dayMap).length)}, 1fr)`;
    container.innerHTML = Object.entries(dayMap).slice(0, 7).map(([day, data]) => {
        const maxTemp = Math.max(...data.map(d => d.main?.temp_max ?? d.temperature ?? 0));
        const minTemp = Math.min(...data.map(d => d.main?.temp_min ?? d.temperature ?? 0));
        let pop = Math.max(...data.map(d => d.pop ?? d.rain_probability ?? 0)); if(pop <= 1) pop *= 100;
        return `<div class="day-card"><div class="day-name">${day}</div><div class="day-icon">${getEmoji(data[0].weather ? data[0].weather[0].main : 'Clear')}</div><div class="day-hi">${Math.round(maxTemp)}°</div><div class="day-lo">${Math.round(minTemp)}°</div><div class="day-rain">💧${Math.round(pop)}%</div></div>`;
    }).join('');
}

function renderTable(items) {
    const tbody = document.getElementById('fcTableBody');
    if (!tbody) return;
    tbody.innerHTML = items.slice(0, 15).map(f => {
        const dt = parseDate(f); const temp = Math.round(f.main?.temp ?? f.temperature ?? 0);
        let pop = f.pop ?? f.rain_probability ?? 0; if(pop <= 1) pop *= 100;
        return `<tr style="border-bottom:1px solid var(--border)"><td style="padding:12px">${dt.getHours()}:00</td><td style="text-align:center;text-transform:capitalize">${f.weather ? f.weather[0].description : 'Clear'}</td><td style="text-align:center;font-weight:600">${temp}°C</td><td style="text-align:center">${Math.round(f.main?.feels_like ?? temp)}°C</td><td style="text-align:center">${f.main?.humidity ?? f.humidity}%</td><td style="text-align:center">${Math.round(f.wind?.speed ?? f.wind_speed)} km/h</td><td style="text-align:center">${Math.round(pop)}%</td></tr>`;
    }).join('');
}

function renderVoiceButton() {
    const existingBtn = document.getElementById('voiceTriggerBtn'); if (existingBtn) existingBtn.remove();
    const statsContainer = document.getElementById('forecastStats'); if (!statsContainer) return;
    const btn = document.createElement('button');
    btn.id = 'voiceTriggerBtn'; btn.innerHTML = '🔊 मौसम की जानकारी सुनें';
    btn.style.cssText = `background: var(--accent); color: white; border: none; padding: 8px 16px; border-radius: 20px; font-weight: 600; cursor: pointer; margin-bottom: 15px; transition: transform 0.2s ease, background 0.2s ease;`;
    btn.onclick = () => { if (currentForecastData) speakForecast(currentForecastData, currentCityName); };
    statsContainer.parentNode.insertBefore(btn, statsContainer);
}

function speakForecast(items, city) {
    if (!window.speechSynthesis) return; window.speechSynthesis.cancel();
    const temp = Math.round(items[0].main?.temp ?? items[0].temperature ?? 0);
    const u = new SpeechSynthesisUtterance(`${city || "आपके इलाके"} का मौसम। अभी तापमान ${temp} डिग्री है।`);
    u.lang = 'hi-IN'; u.rate = 0.95; window.speechSynthesis.speak(u);
}

function getEmoji(m) { return { Clear:'☀️', Clouds:'☁️', Rain:'🌧️', Drizzle:'🌦️', Thunderstorm:'⛈️' }[m] || '🌡️'; }
function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val; }