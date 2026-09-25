import React from 'react';
import { clsx } from 'clsx';
import './ui.css';

export const IconButton = ({ children, className, variant = 'ghost', ...props }) => {
  return (
    <button 
      className={clsx('icon-btn', `icon-btn-${variant}`, className)} 
      {...props}
    >
      {children}
    </button>
  );
};
