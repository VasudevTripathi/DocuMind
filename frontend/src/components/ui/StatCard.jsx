import React from 'react';
import { clsx } from 'clsx';
import './ui.css';

export const StatCard = ({ title, value, change, trend = 'up', icon, className }) => {
  return (
    <div className={clsx('stat-card glass-panel', className)}>
      <div className="stat-card-icon">{icon}</div>
      <div className="stat-card-content">
        <div className="stat-card-header">
          <span className="stat-value">{value}</span>
          {change && (
            <span className={clsx('stat-change', trend === 'up' ? 'text-success' : 'text-danger')}>
              {trend === 'up' ? '+' : ''}{change}
            </span>
          )}
        </div>
        <div className="stat-title text-secondary">{title}</div>
      </div>
    </div>
  );
};
