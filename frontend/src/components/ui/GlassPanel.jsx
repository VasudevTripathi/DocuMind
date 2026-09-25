import React from 'react';
import { clsx } from 'clsx';
import './ui.css';

export const GlassPanel = ({ children, className, ...props }) => {
  return (
    <div 
      className={clsx('glass-panel', className)} 
      {...props}
    >
      {children}
    </div>
  );
};
