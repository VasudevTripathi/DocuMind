import React from 'react';

export const DocumentSkeleton = ({ count = 4, isMobile = false }) => {
  const items = Array.from({ length: count });

  if (isMobile) {
    return (
      <div className="skeleton-cards-container" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        {items.map((_, idx) => (
          <div 
            key={idx} 
            className="glass-panel"
            style={{ 
              padding: 'var(--space-4)', 
              borderRadius: 'var(--radius-md)', 
              display: 'flex', 
              flexDirection: 'column', 
              gap: 'var(--space-3)' 
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              <div className="skeleton-shimmer" style={{ width: '36px', height: '36px', borderRadius: 'var(--radius-sm)' }} />
              <div style={{ flex: 1 }}>
                <div className="skeleton-shimmer" style={{ width: '65%', height: '14px', borderRadius: '4px', marginBottom: '6px' }} />
                <div className="skeleton-shimmer" style={{ width: '35%', height: '10px', borderRadius: '4px' }} />
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 'var(--space-2)', borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div className="skeleton-shimmer" style={{ width: '70px', height: '20px', borderRadius: 'var(--radius-full)' }} />
              <div className="skeleton-shimmer" style={{ width: '50px', height: '12px', borderRadius: '4px' }} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      {items.map((_, idx) => (
        <tr key={idx} className="skeleton-row">
          <td style={{ padding: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              <div className="skeleton-shimmer" style={{ width: '24px', height: '24px', borderRadius: '4px', flexShrink: 0 }} />
              <div className="skeleton-shimmer" style={{ width: '200px', height: '14px', borderRadius: '4px' }} />
            </div>
          </td>
          <td style={{ padding: 'var(--space-4)' }}>
            <div className="skeleton-shimmer" style={{ width: '60px', height: '14px', borderRadius: '4px' }} />
          </td>
          <td style={{ padding: 'var(--space-4)' }}>
            <div className="skeleton-shimmer" style={{ width: '50px', height: '14px', borderRadius: '4px' }} />
          </td>
          <td style={{ padding: 'var(--space-4)' }}>
            <div className="skeleton-shimmer" style={{ width: '75px', height: '14px', borderRadius: '4px' }} />
          </td>
          <td style={{ padding: 'var(--space-4)' }}>
            <div className="skeleton-shimmer" style={{ width: '80px', height: '22px', borderRadius: 'var(--radius-full)' }} />
          </td>
          <td style={{ padding: 'var(--space-4)', textAlign: 'right' }}>
            <div className="skeleton-shimmer" style={{ width: '28px', height: '28px', borderRadius: 'var(--radius-sm)', marginLeft: 'auto' }} />
          </td>
        </tr>
      ))}
    </>
  );
};
