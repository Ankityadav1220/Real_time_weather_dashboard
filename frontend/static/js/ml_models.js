/**
 * WeatherIQ — ML Models Page JS
 */
'use strict';
let charts={}, city=getCurrentCity();
Chart.defaults.color='#94a3b8'; Chart.defaults.borderColor='rgba(99,179,237,.08)';
Chart.defaults.font.family="'JetBrains Mono',monospace"; Chart.defaults.font.size=11;
const $=id=>document.getElementById(id);
const txt=(id,v)=>{const e=$(id);if(e)e.textContent=v};
const htm=(id,h)=>{const e=$(id);if(e)e.innerHTML=h};
async function api(p){const r=await fetch('/api'+p);if(!r.ok)throw new Error(r.status);return r.json()}

let metricsRetry=null;

function renderModelCard(prefix,m,isBest){
  const card=$(prefix+'-card');
  if(!m||Object.keys(m).length===0){
    txt(prefix+'-mae','…');txt(prefix+'-rmse','…');txt(prefix+'-r2','…');txt(prefix+'-mape','…');txt(prefix+'-samples','…');
    if(card)card.classList.remove('best');
    return;
  }
  txt(prefix+'-mae',  m.mae!==undefined  ? m.mae.toFixed(3)  :'--');
  txt(prefix+'-rmse', m.rmse!==undefined ? m.rmse.toFixed(3) :'--');
  txt(prefix+'-r2',   m.r2_score!==undefined?m.r2_score.toFixed(4):'--');
  txt(prefix+'-mape', m.mape!==undefined  ? m.mape.toFixed(1)+'%':'--');
  txt(prefix+'-samples',m.train_size||m.training_samples||'--');
  const r2=m.r2_score||0;
  const fill=$(prefix+'-fill');if(fill){fill.style.width=Math.max(0,r2*100)+'%';fill.style.background=r2>0.9?'#10b981':r2>0.7?'#f59e0b':'#f43f5e'}
  txt(prefix+'-r2-pct',(r2*100).toFixed(1)+'%');
  const badge=$(prefix+'-badge');
  if(badge)badge.style.display=isBest?'inline-block':'none';
  if(card)card.classList.toggle('best',isBest);
}

function renderMetrics(metrics){
  if(!metrics||Object.keys(metrics).length===0)return;
  const best=metrics.best_model||'';
  const map={linear_regression:'lr',random_forest:'rf',lstm:'lstm'};
  for(const[model,prefix]of Object.entries(map)){
    renderModelCard(prefix,metrics[model],model===best);
  }
  renderCompareCharts(metrics);
  renderFeatureImportance(metrics.random_forest?.top_features||[]);
}

function renderCompareCharts(metrics){
  const models=['Linear Regression','Random Forest','LSTM'];
  const keys=['linear_regression','random_forest','lstm'];
  const r2vals=keys.map(k=>metrics[k]?.r2_score??0);
  const maevals=keys.map(k=>metrics[k]?.mae??0);
  const rmsevals=keys.map(k=>metrics[k]?.rmse??0);
  const colors=['#06b6d4','#10b981','#8b5cf6'];

  if(charts.r2)charts.r2.destroy();
  charts.r2=new Chart($('r2Chart'),{type:'bar',data:{labels:models,datasets:[{
    label:'R² Score',data:r2vals,
    backgroundColor:colors.map(c=>c+'99'),borderColor:colors,borderWidth:1.5,borderRadius:8
  }]},options:{responsive:true,maintainAspectRatio:false,animation:{duration:600},plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>`R² = ${ctx.raw.toFixed(4)}`},backgroundColor:'rgba(10,20,40,.95)',padding:10}},scales:{x:{grid:{color:'rgba(99,179,237,.06)'}},y:{grid:{color:'rgba(99,179,237,.06)'},min:0,max:1,title:{display:true,text:'R² Score',color:'#94a3b8'}}}}});

  if(charts.error)charts.error.destroy();
  charts.error=new Chart($('errorChart'),{type:'bar',data:{labels:models,datasets:[
    {label:'MAE',data:maevals,backgroundColor:'rgba(245,158,11,.7)',borderColor:'#f59e0b',borderWidth:1,borderRadius:6},
    {label:'RMSE',data:rmsevals,backgroundColor:'rgba(244,63,94,.6)',borderColor:'#f43f5e',borderWidth:1,borderRadius:6}
  ]},options:{responsive:true,maintainAspectRatio:false,animation:{duration:600},plugins:{legend:{display:true,labels:{color:'#94a3b8',boxWidth:10,padding:14}},tooltip:{backgroundColor:'rgba(10,20,40,.95)',padding:10}},scales:{x:{grid:{color:'rgba(99,179,237,.06)'}},y:{grid:{color:'rgba(99,179,237,.06)'},beginAtZero:true,title:{display:true,text:'Error',color:'#94a3b8'}}}}});
}

function renderFeatureImportance(features){
  if(!features||!features.length){
    htm('featureImportance','<div style="color:var(--text-3);font-size:.82rem;padding:10px">Feature importance data not yet available. Train the Random Forest model first.</div>');
    return;
  }
  htm('featureImportance',features.map((f,i)=>{
    const pct=Math.round(100-i*12);
    return`<div class="fi-row">
      <div class="fi-name">${f}</div>
      <div class="fi-bar-wrap"><div class="fi-bar" style="width:${pct}%"></div></div>
      <div class="fi-pct">${pct}%</div>
    </div>`;
  }).join(''));
}

async function loadPredictions(){
  const target=$('predTarget')?.value||'temperature';
  const c=$('trainCity')?.value||city;
  try{
    const r=await api(`/prediction?city=${encodeURIComponent(c)}&target=${target}&steps=10`);
    if(!r.success)throw new Error(r.error);
    renderPredChart(r.data,target);
  }catch(e){showToast(e.message,'error')}
}
window.loadPredictions=loadPredictions;

function renderPredChart(preds,target){
  if(charts.pred)charts.pred.destroy();
  const units={temperature:'°C',humidity:'%',wind_speed:'km/h'};
  const colors={temperature:'#f59e0b',humidity:'#8b5cf6',wind_speed:'#10b981'};
  const color=colors[target]||'#06b6d4';
  charts.pred=new Chart($('predChart'),{type:'line',data:{
    labels:preds.map(p=>`+${p.hours_ahead}h`),
    datasets:[{
      label:`Predicted ${target} (${units[target]||''})`,
      data:preds.map(p=>p.predicted_value),
      borderColor:color,backgroundColor:color+'20',
      borderWidth:2.5,pointRadius:5,fill:true,tension:.4,pointBackgroundColor:color
    }]
  },options:{responsive:true,maintainAspectRatio:false,animation:{duration:600},plugins:{legend:{labels:{color:'#94a3b8',boxWidth:10}},tooltip:{backgroundColor:'rgba(10,20,40,.95)',padding:10,bodyColor:'#e2e8f0'}},scales:{x:{grid:{color:'rgba(99,179,237,.06)'}},y:{grid:{color:'rgba(99,179,237,.06)'},title:{display:true,text:units[target]||'',color:'#94a3b8'}}}}});
}

async function trainModels(){
  const trainCity=$('trainCity')?.value||city;
  const target=$('trainTarget')?.value||'temperature';
  const btn=$('trainBtn');
  const status=$('trainStatus');
  const log=$('trainLog');
  btn.disabled=true;btn.textContent='⏳ Training…';
  if(status)status.textContent='Training';
  if(log){log.style.display='block';log.innerHTML=''}
  const logLine=msg=>{if(log)log.innerHTML+=`<div>▶ ${msg}</div>`;};
  logLine(`Starting training on ${trainCity} / target: ${target}`);
  logLine('Fetching 30 days of historical data…');
  showToast(`Training on ${trainCity}…`,'info',12000);
  try{
    const r=await fetch('/api/train',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({city:trainCity,target})});
    const d=await r.json();
    if(d.success){
      logLine(`✅ Training complete — best model: ${d.results?.best_model}`);
      logLine(`Samples used: ${d.training_samples}`);
      if(status)status.textContent='Complete';
      showToast(`Training complete! Best: ${d.results?.best_model}`,'success');
      await loadMetrics();
      await loadPredictions();
    }else{
      logLine(`❌ ${d.message||d.error||'Training failed'}`);
      showToast(d.message||'Training failed','error');
      if(status)status.textContent='Failed';
    }
  }catch(e){logLine(`❌ Error: ${e.message}`);showToast(e.message,'error')}
  finally{btn.disabled=false;btn.textContent='🚀 Train All Models'}
}
window.trainModels=trainModels;

async function loadMetrics(){
  try{
    const r=await api('/model-metrics');
    if(r.success&&r.metrics&&Object.keys(r.metrics).length){
      renderMetrics(r.metrics);
      const any=Object.values(r.metrics).some(m=>m&&m.r2_score!==undefined);
      if(!any)scheduleRetry();
    }else{scheduleRetry()}
  }catch(e){scheduleRetry()}
}
window.loadMetrics=loadMetrics;

function scheduleRetry(){
  clearTimeout(metricsRetry);
  metricsRetry=setTimeout(loadMetrics,8000);
}

document.addEventListener('DOMContentLoaded',()=>{
  loadMetrics();
  loadPredictions();
  $('predTarget')?.addEventListener('change',loadPredictions);
  window.addEventListener('cityChange',e=>{city=e.detail.city;if($('trainCity'))$('trainCity').value=city;});
  setTimeout(()=>{if(!Object.keys({}).length)scheduleRetry()},5000);
});
