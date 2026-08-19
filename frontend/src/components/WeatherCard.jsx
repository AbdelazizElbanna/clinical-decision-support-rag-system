import React, { useState } from 'react';
import { Thermometer, Droplets, Sun, Wind, CloudFog, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

export default function WeatherCard({ weatherData }) {
  const [expanded, setExpanded] = useState(false);
  
  if (!weatherData || !weatherData.data) return null;
  
  const { data, governorate_ar, governorate_en } = weatherData;
  const hasAlerts = data.skin_alerts && data.skin_alerts.length > 0;
  const isSafe = data.skin_alerts?.length === 1 && data.skin_alerts[0].includes('safe');

  return (
    <div className="glass" style={{
      borderRadius: 'var(--radius)',
      padding: '20px',
      marginBottom: '20px',
      border: `1px solid ${isSafe ? 'var(--border)' : 'rgba(251,191,36,0.3)'}`,
      boxShadow: '0 8px 32px rgba(0,0,0,0.2)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: '600', color: 'var(--text)' }}>
            {governorate_en} <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>({governorate_ar})</span>
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Live Environment Data</p>
        </div>
        {!isSafe && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--warning)', fontSize: '0.8rem', fontWeight: '600', background: 'rgba(245,158,11,0.1)', padding: '4px 8px', borderRadius: '4px' }}>
            <AlertTriangle size={16} /> Attention
          </div>
        )}
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))',
        gap: '12px',
        marginBottom: '16px'
      }}>
        <Metric icon={<Thermometer size={18} color="var(--accent)" />} label="Temp" value={`${data.temperature_c}°C`} />
        <Metric icon={<Droplets size={18} color="#3b82f6" />} label="Humidity" value={`${data.humidity_percent}%`} />
        <Metric icon={<Sun size={18} color="#eab308" />} label="UV Index" value={data.uv_index} />
        <Metric icon={<CloudFog size={18} color="#a8a29e" />} label="Dust" value={`${data.dust || 0} µg/m³`} />
      </div>

      {hasAlerts && (
        <div style={{ background: 'var(--surface-2)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
          <button 
            onClick={() => setExpanded(!expanded)}
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px',
              background: 'transparent',
              border: 'none',
              color: 'var(--text)',
              cursor: 'pointer',
              fontSize: '0.9rem',
              fontWeight: '500'
            }}
          >
            Skin Risk Alerts ({data.skin_alerts.length})
            {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
          
          {expanded && (
            <div style={{ padding: '0 12px 12px 12px' }}>
              <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                {data.skin_alerts.map((alert, i) => (
                  <li key={i} style={{ marginBottom: '6px', color: alert.includes('safe') ? 'var(--success)' : 'var(--text)' }}>
                    {alert}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Metric({ icon, label, value }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
      {icon}
      <div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{label}</div>
        <div style={{ fontSize: '0.95rem', fontWeight: '600', color: 'var(--text)' }}>{value}</div>
      </div>
    </div>
  );
}
