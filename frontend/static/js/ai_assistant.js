'use strict';
let city=getCurrentCity(),isTyping=false;
const $=id=>document.getElementById(id);
const htm=(id,h)=>{const e=$(id);if(e)e.innerHTML=h};
async function api(p,o){const r=await fetch(p,o||{});if(!r.ok)throw new Error(r.status);return r.json()}

function addMessage(text,role='ai'){
  const msgs=$('chatMessages');if(!msgs)return;
  const div=document.createElement('div');
  div.className=`chat-msg ${role}`;
  div.innerHTML=`<div class="chat-avatar ${role==='ai'?'ai':'usr'}">${role==='ai'?'🤖':'👤'}</div><div class="chat-bubble">${text}</div>`;
  msgs.appendChild(div);
  msgs.scrollTop=msgs.scrollHeight;
}

function addTyping(){
  const msgs=$('chatMessages');if(!msgs)return;
  const div=document.createElement('div');
  div.className='chat-msg ai';div.id='typingIndicator';
  div.innerHTML=`<div class="chat-avatar ai">🤖</div><div class="chat-bubble" style="color:var(--text-3)">⏳ Thinking…</div>`;
  msgs.appendChild(div);msgs.scrollTop=msgs.scrollHeight;
}

function removeTyping(){
  const t=$('typingIndicator');if(t)t.remove();
}

async function sendChat(){
  const input=$('chatInput');if(!input||isTyping)return;
  const msg=input.value.trim();if(!msg)return;
  input.value='';addMessage(msg,'user');addTyping();isTyping=true;
  try{
    const r=await api('/api/intelligence/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg,city})});
    removeTyping();
    if(r.success)addMessage(r.reply,'ai');
    else addMessage('Sorry, I had trouble understanding that. Please try again.','ai');
  }catch(e){removeTyping();addMessage('Connection error. Please check your server is running.','ai');}
  finally{isTyping=false;}
}
window.sendChat=sendChat;

function quickAsk(q){
  const input=$('chatInput');if(input)input.value=q;sendChat();
}
window.quickAsk=quickAsk;

async function loadWeatherPanel(){
  try{
    const r=await api(`/api/current-weather?city=${encodeURIComponent(city)}`);
    if(!r.success)return;
    const w=r.data;
    htm('assistantWeather',`
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:.82rem">
        <div><span style="color:var(--text-3)">Temp</span><div style="font-weight:600;color:var(--accent);font-family:var(--mono)">${w.temperature}°C</div></div>
        <div><span style="color:var(--text-3)">Condition</span><div style="font-weight:600">${w.weather_description||w.weather_main}</div></div>
        <div><span style="color:var(--text-3)">Humidity</span><div style="font-weight:600;font-family:var(--mono)">${w.humidity}%</div></div>
        <div><span style="color:var(--text-3)">Wind</span><div style="font-weight:600;font-family:var(--mono)">${w.wind_speed} km/h</div></div>
        <div><span style="color:var(--text-3)">AQI</span><div style="font-weight:600">${w.aqi_info?.label||'--'}</div></div>
        <div><span style="color:var(--text-3)">City</span><div style="font-weight:600">${w.city}, ${w.country||''}</div></div>
      </div>`);
    const tips=w.activity_recommendations||[];
    htm('smartTips',tips.map(t=>`<div style="background:rgba(255,255,255,.03);border:1px solid var(--border);border-radius:6px;padding:8px 10px;font-size:.78rem;color:var(--text-2)">${t}</div>`).join(''));
    applyWeatherBackground(w.weather_main);
  }catch(e){}
}

document.addEventListener('DOMContentLoaded',()=>{
  loadWeatherPanel();
  $('chatInput')?.addEventListener('keydown',e=>{if(e.key==='Enter')sendChat();});
  window.addEventListener('cityChange',e=>{
    city=e.detail.city;loadWeatherPanel();
    addMessage(`Switched to ${city}. Ask me anything about the weather there! 🌍`,'ai');
  });
  setTimeout(()=>addMessage(`Current city: ${city}. What would you like to know? 😊`,'ai'),800);
});
