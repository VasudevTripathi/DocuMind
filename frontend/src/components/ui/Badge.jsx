import React from 'react';
import { clsx } from 'clsx';
import './ui.css';

export const Badge = ({ children, variant = 'default', className, icon, ...props }) => {
  return (
    <span 
      className={clsx('badge', `badge-${variant}`, className)} 
      {...props}
    >
      {icon && <span className="badge-icon">{icon}</span>}
      {children}
    </span>
  );
};
