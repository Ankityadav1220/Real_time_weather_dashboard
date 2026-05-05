"""
Nowcasting Engine
Detects sudden weather changes in the next 30–90 minutes.
Uses gradient analysis + anomaly detection on recent observations.
"""
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class NowcastEngine:
    """
    Analyses last N hours of observations to detect:
    - Rapid temperature drops / rises
    - Sudden rain onset
    - Wind speed spikes
    - Pressure falls (precursor to storms)
    """

    THRESHOLDS = {
        'temp_drop_per_hour':   -3.0,   # °C/hr — rapid cooling
        'temp_rise_per_hour':    3.0,
        'pressure_drop_per_3h': -3.0,   # hPa — storm indicator
        'wind_spike_factor':     1.8,    # >1.8× recent mean
        'rain_onset_threshold':  2.0,    # mm/hr from dry
        'humidity_spike':       15,      # % jump in 1hr
    }

    def analyse(self, observations: list) -> dict:
        if len(observations) < 3:
            return self._empty_nowcast()

        # Sort by time ascending
        obs = sorted(observations, key=lambda x: x.get('recorded_at', ''))[-12:]

        temps     = [o.get('temperature', 20) for o in obs]
        pressures = [o.get('pressure', 1013) for o in obs]
        winds     = [o.get('wind_speed', 10) for o in obs]
        humids    = [o.get('humidity', 60) for o in obs]
        rains     = [o.get('rain_1h', 0) for o in obs]

        events = []

        # ── Temperature gradient ──────────────────────────────────────────
        if len(temps) >= 3:
            recent_trend = (temps[-1] - temps[-3]) / 2   # per hour approx
            if recent_trend <= self.THRESHOLDS['temp_drop_per_hour']:
                events.append({
                    'type': 'temp_drop',
                    'severity': 'high' if recent_trend < -5 else 'medium',
                    'icon': '🌡️↓',
                    'title': 'Rapid Temperature Drop Detected',
                    'detail': f'Temperature falling {abs(recent_trend):.1f}°C/hr. Expected to reach {temps[-1]+recent_trend*2:.1f}°C in 2 hours.',
                    'eta_min': 30,
                    'confidence': 78,
                })
            elif recent_trend >= self.THRESHOLDS['temp_rise_per_hour']:
                events.append({
                    'type': 'temp_rise',
                    'severity': 'low',
                    'icon': '🌡️↑',
                    'title': 'Temperature Rising Quickly',
                    'detail': f'Temperature rising {recent_trend:.1f}°C/hr. Expect {temps[-1]+recent_trend*1:.1f}°C in 1 hour.',
                    'eta_min': 30,
                    'confidence': 72,
                })

        # ── Pressure drop (storm precursor) ───────────────────────────────
        if len(pressures) >= 4:
            p_trend = pressures[-1] - pressures[-4]
            if p_trend <= self.THRESHOLDS['pressure_drop_per_3h']:
                events.append({
                    'type': 'pressure_drop',
                    'severity': 'high',
                    'icon': '⏬',
                    'title': 'Pressure Drop — Possible Storm Incoming',
                    'detail': f'Barometric pressure fell {abs(p_trend):.1f} hPa in 3 hours — classic pre-storm signal.',
                    'eta_min': 45,
                    'confidence': 82,
                })

        # ── Wind spike detection ──────────────────────────────────────────
        wind_mean = np.mean(winds[:-2]) if len(winds) > 2 else np.mean(winds)
        if wind_mean > 0 and winds[-1] > wind_mean * self.THRESHOLDS['wind_spike_factor']:
            factor = winds[-1] / wind_mean
            events.append({
                'type': 'wind_spike',
                'severity': 'medium' if winds[-1] < 50 else 'high',
                'icon': '💨',
                'title': 'Wind Speed Spike',
                'detail': f'Wind jumped to {winds[-1]} km/h ({factor:.1f}× normal). Gusts likely in the next 30 minutes.',
                'eta_min': 15,
                'confidence': 70,
            })

        # ── Rain onset ────────────────────────────────────────────────────
        if rains[-1] < 0.5 and any(r > self.THRESHOLDS['rain_onset_threshold'] for r in rains[-3:]):
            events.append({
                'type': 'rain_onset',
                'severity': 'medium',
                'icon': '🌧️',
                'title': 'Rain Approaching',
                'detail': 'Rainfall detected nearby. Expect precipitation to reach your area in 20–40 minutes.',
                'eta_min': 25,
                'confidence': 75,
            })

        # ── Humidity spike ────────────────────────────────────────────────
        if len(humids) >= 3:
            h_change = humids[-1] - humids[-3]
            if h_change >= self.THRESHOLDS['humidity_spike']:
                events.append({
                    'type': 'humidity_spike',
                    'severity': 'low',
                    'icon': '💧',
                    'title': 'Humidity Rising Fast',
                    'detail': f'Humidity rose {h_change:.0f}% in recent hours — often precedes rain or fog formation.',
                    'eta_min': 45,
                    'confidence': 65,
                })

        # ── Predict next 90-min values ────────────────────────────────────
        projections = self._project_values(temps, pressures, winds, rains)

        return {
            'events': events,
            'alert_count': len([e for e in events if e['severity'] in ('high', 'medium')]),
            'current': {
                'temp': temps[-1], 'pressure': pressures[-1],
                'wind': winds[-1], 'humidity': humids[-1], 'rain': rains[-1]
            },
            'trends': {
                'temp_trend':     round((temps[-1] - temps[0]) / max(len(temps)-1, 1), 2),
                'pressure_trend': round((pressures[-1] - pressures[0]) / max(len(pressures)-1, 1), 2),
                'wind_trend':     round((winds[-1] - winds[0]) / max(len(winds)-1, 1), 2),
            },
            'projections': projections,
            'generated_at': datetime.utcnow().isoformat(),
        }

    def _project_values(self, temps, pressures, winds, rains):
        """Linear extrapolation with damping for 15/30/45/60/90 min"""
        def project(series, steps):
            if len(series) < 2:
                return [series[-1]] * steps
            x = np.arange(len(series))
            try:
                coef = np.polyfit(x, series, 1)
                trend = coef[0]
                # Damp trend over time
                return [round(series[-1] + trend * (i+1) * 0.7, 1) for i in range(steps)]
            except Exception:
                return [series[-1]] * steps

        now = datetime.utcnow()
        intervals = [15, 30, 45, 60, 90]
        t_proj = project(temps, 5)
        p_proj = project(pressures, 5)
        w_proj = project(winds, 5)

        return [
            {
                'time': (now + timedelta(minutes=m)).strftime('%H:%M'),
                'minutes': m,
                'temp': t_proj[i],
                'pressure': p_proj[i],
                'wind': max(0, w_proj[i]),
            }
            for i, m in enumerate(intervals)
        ]

    def _empty_nowcast(self):
        return {
            'events': [],
            'alert_count': 0,
            'current': {},
            'trends': {},
            'projections': [],
            'generated_at': datetime.utcnow().isoformat(),
        }

    # ── Anomaly score (0–100) ────────────────────────────────────────────
    def anomaly_score(self, obs: list) -> int:
        if len(obs) < 5:
            return 0
        vals  = [o.get('temperature', 20) for o in obs]
        mean  = np.mean(vals[:-1])
        std   = np.std(vals[:-1]) + 0.01
        z     = abs(vals[-1] - mean) / std
        score = min(100, int(z * 20))
        return score
