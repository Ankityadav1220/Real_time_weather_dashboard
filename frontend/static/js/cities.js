/**
 * WeatherIQ — Multi-City Comparison Page JS
 */
'use strict';
const ICONS={Clear:'☀️',Clouds:'⛅',Rain:'🌧️',Drizzle:'🌦️',Thunderstorm:'⛈️',Snow:'❄️',Mist:'🌫️',Fog:'🌫️',Haze:'🌫️'};
const CHART_COLORS=['#06b6d4','#f59e0b','#10b981','#8b5cf6','#f43f5e','#38bdf8'];
const DEFAULT_CITIES=['Delhi','Mumbai','London','New York','Tokyo','Dubai'];
const MAX_CITIES=6;
let cities=[], weatherData={}, charts={};

Chart.defaults.color='#94a3b8'; Chart.defaults.borderColor='rgba(99,179,237,.08)';
Chart.defaults.font.family="'JetBrains Mono',monospace"; Chart.defaults.font.size=11;
const $=id=>document.getElementById(id);
const htm=(id,h)=>{const e=$(id);if(e)e.innerHTML=h};
async function api(p){const r=await fetch('/api'+p);if(!r.ok)throw new Error(r.status);return r.json()}

function setupLocalAutocomplete(){
  const input=$('cityAddInput');
  const list=$('cityAddAC');
  if(!input||!list)return;
  let timer;
  input.addEventListener('input',()=>{
    clearTimeout(timer);
    const q=input.value.trim();
    if(!q){list.classList.remove('open');return}
    timer=setTimeout(async()=>{
      const r=await fetch(`/api/autocomplete?q=${encodeURIComponent(q)}`);
      const cs=await r.json();
      list.innerHTML=cs.map(c=>`<div class="ac-item" data-city="${c}">${c}</div>`).join('');
      list.classList.toggle('open',cs.length>0);
      list.querySelectorAll('.ac-item').forEach(el=>{
        el.addEventListener('click',()=>{input.value=el.dataset.city;list.classList.remove('open')});
      });
    },200);
  });
  input.addEventListener('keydown',e=>{if(e.key==='Enter')addCity(input.value.trim())});
  document.addEventListener('click',e=>{if(!input.contains(e.target))list.classList.remove('open')});
}

async function addCity(name){
  name=name.trim();
  if(!name||cities.includes(name)||cities.length>=MAX_CITIES){
    if(cities.length>=MAX_CITIES)showToast(`Max ${MAX_CITIES} cities`,'error');
    return;
  }
  cities.push(name);
  renderTags();
  await fetchCity(name);
  renderGrid();
  renderCompareChart();
  renderRankTable();
  updateBadge();
}

function removeCity(name){
  cities=cities.filter(c=>c!==name);
  delete weatherData[name];
  renderTags();
  renderGrid();
  renderCompareChart();
  renderRankTable();
  updateBadge();
}

async function fetchCity(name){
  try{
    const r=await api(`/current-weather?city=${encodeURIComponent(name)}`);
    if(r.success)weatherData[name]=r.data;
  }catch(e){showToast(`Failed: ${name}`,'error')}
}

function updateBadge(){
  const el=$('cityCountBadge');
  if(el)el.textContent=`${cities.length} / ${MAX_CITIES}`;
}

function renderTags(){
  htm('cityTags',cities.map(c=>`
    <div class="city-tag">
      <span>${c}</span>
      <button onclick="removeCity('${c}')" title="Remove">✕</button>
    </div>`).join(''));
}

function renderGrid(){
  const grid=$('cityGrid');
  if(!grid)return;
  grid.innerHTML=cities.map((c,i)=>{
    const w=weatherData[c];
    if(!w)return`<div class="city-card" style="animation-delay:${i*0.06}s"><div style="text-align:center;padding:20px;color:var(--text-3)">Loading ${c}…</div></div>`;
    const color=CHART_COLORS[i%CHART_COLORS.length];
    const icon=ICONS[w.weather_main]||'🌡️';
    return`<div class="city-card" style="animation-delay:${i*0.06}s;border-top:3px solid ${color}">
      <button class="city-remove" onclick="removeCity('${c}')">✕</button>
      <div class="city-card-top">
        <div><div class="city-name-lbl">${w.city}</div><div class="city-country">${w.country||''}</div></div>
        <span style="font-size:1.8rem">${icon}</span>
      </div>
      <div class="city-temp" style="color:${color}">${w.temperature}°C</div>
      <div class="city-desc">${w.weather_description||''}</div>
      ${w.is_mock?'<span style="font-size:.62rem;color:var(--warning)">simulated</span>':''}
      <div class="city-metrics">
        <div class="cm-item"><div class="cm-val">${w.humidity}%</div><div class="cm-lbl">Humidity</div></div>
        <div class="cm-item"><div class="cm-val">${w.wind_speed}</div><div class="cm-lbl">km/h</div></div>
        <div class="cm-item"><div class="cm-val">${w.aqi_info?.value||'--'}</div><div class="cm-lbl">AQI</div></div>
      </div>
    </div>`;
  }).join('');
}

function renderCompareChart(){
  if(charts.compare)charts.compare.destroy();
  const metric=$('compareMetric')?.value||'temperature';
  const labels={'temperature':'Temperature (°C)','humidity':'Humidity (%)','wind_speed':'Wind Speed (km/h)','pressure':'Pressure (hPa)'};
  const validCities=cities.filter(c=>weatherData[c]);
  if(!validCities.length)return;
  const data=validCities.map(c=>weatherData[c][metric]||0);
  charts.compare=new Chart($('compareChart'),{
    type:'bar',
    data:{labels:validCities,datasets:[{
      label:labels[metric]||metric,
      data,
      backgroundColor:validCities.map((_,i)=>CHART_COLORS[i%CHART_COLORS.length]+'99'),
      borderColor:validCities.map((_,i)=>CHART_COLORS[i%CHART_COLORS.length]),
      borderWidth:1.5,borderRadius:6,
    }]},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},plugins:{legend:{display:false},tooltip:{backgroundColor:'rgba(10,20,40,.95)',padding:10,bodyColor:'#e2e8f0'}},scales:{x:{grid:{color:'rgba(99,179,237,.06)'}},y:{grid:{color:'rgba(99,179,237,.06)'},beginAtZero:false}}}
  });
}

function renderRankTable(){
  const validCities=cities.filter(c=>weatherData[c]);
  const sorted=[...validCities].sort((a,b)=>(weatherData[b].temperature||0)-(weatherData[a].temperature||0));
  htm('rankBody',sorted.map((c,i)=>{
    const w=weatherData[c];
    const icon=ICONS[w.weather_main]||'🌡️';
    const medals=['🥇','🥈','🥉'];
    return`<tr class="rank-row">
      <td class="rank-cell" style="font-weight:700;color:var(--accent)">${medals[i]||i+1}</td>
      <td class="rank-cell" style="font-weight:600">${c}</td>
      <td class="rank-cell" style="text-align:center;font-family:var(--mono);color:var(--accent)">${w.temperature}°C</td>
      <td class="rank-cell" style="text-align:center;font-family:var(--mono)">${w.humidity}%</td>
      <td class="rank-cell" style="text-align:center;font-family:var(--mono)">${w.wind_speed} km/h</td>
      <td class="rank-cell" style="text-align:center;font-family:var(--mono)">${w.aqi_info?.label||'--'}</td>
      <td class="rank-cell" style="text-align:center">${icon} ${w.weather_main}</td>
    </tr>`;
  }).join(''));
}

async function refreshAll(){
  setLoader(true,'Refreshing all cities…');
  await Promise.all(cities.map(c=>fetchCity(c)));
  renderGrid(); renderCompareChart(); renderRankTable();
  showToast('All cities refreshed','success');
  setLoader(false);
}

async function loadPresets(){
  cities=[];weatherData={};
  setLoader(true,'Loading default cities…');
  await Promise.all(DEFAULT_CITIES.map(async c=>{cities.push(c);await fetchCity(c);}));
  renderTags(); renderGrid(); renderCompareChart(); renderRankTable(); updateBadge();
  showToast('Default cities loaded','success');
  setLoader(false);
}
window.loadPresets=loadPresets;
window.removeCity=removeCity;

document.addEventListener('DOMContentLoaded',()=>{
  setupLocalAutocomplete();
  $('addCityBtn')?.addEventListener('click',()=>addCity($('cityAddInput').value));
  $('refreshAllBtn')?.addEventListener('click',refreshAll);
  $('compareMetric')?.addEventListener('change',renderCompareChart);
  loadPresets();
  window.addEventListener('cityChange',e=>{
    if(!cities.includes(e.detail.city))addCity(e.detail.city);
  });
});
