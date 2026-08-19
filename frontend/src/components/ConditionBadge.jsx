import React from 'react';

export default function ConditionBadge({ condition }) {
  if (!condition || condition === 'Unknown' || condition === 'General') return null;

  let bg = 'var(--surface-2)';
  let color = 'var(--text)';

  const normalized = condition.toLowerCase();
  if (normalized.includes('eczema')) {
    bg = 'rgba(99, 102, 241, 0.2)'; // primary
    color = 'var(--primary)';
  } else if (normalized.includes('psoriasis')) {
    bg = 'rgba(34, 211, 238, 0.2)'; // accent
    color = 'var(--accent)';
  } else if (normalized.includes('urticaria')) {
    bg = 'rgba(245, 158, 11, 0.2)'; // warning
    color = 'var(--warning)';
  }

  return (
    <div style={{
      display: 'inline-block',
      padding: '4px 12px',
      borderRadius: '999px',
      background: bg,
      color: color,
      fontSize: '0.75rem',
      fontWeight: '600',
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
      marginBottom: '8px'
    }}>
      {condition}
    </div>
  );
}
