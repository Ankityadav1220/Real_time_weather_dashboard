'use strict';
window.addEventListener('wiq:location', loadAlerts);
document.addEventListener('DOMContentLoaded', loadAlerts);

async function loadAlerts() {
  try {
    const r = await fetch(`/api/alerts?${window.locationParams()}`);
    const d = await r.json();
    renderAlerts(d.data || d.alerts || []);
    setText('alertsCity', window.WIQ.displayName || window.WIQ.city);
  } catch(e) { console.error('Alerts error:', e); }
}

function renderAlerts(alerts) {
  setText('alertCount', alerts.length);
  const list = document.getElementById('alertsList');
  if (!list) return;
  if (!alerts.length) {
    list.innerHTML = `<div class="empty-state">✅ <span>No active weather alerts for this location.</span></div>`;
    return;
  }
  list.innerHTML = alerts.map(a => `
    <div class="alert-card sev-${(a.severity||'').toLowerCase()}">
      <div class="alert-header">
        <span class="alert-type-badge">${a.type}</span>
        <span class="alert-sev-badge sev-${(a.severity||'').toLowerCase()}">${a.severity}</span>
      </div>
      <p class="alert-message">${a.message}</p>
    </div>
  `).join('');
}
function setText(id, val) { const e = document.getElementById(id); if(e) e.textContent=val; }
