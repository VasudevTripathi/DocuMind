import React from 'react';
import { clsx } from 'clsx';
import './ui.css';

export const ClayPanel = ({ children, className, ...props }) => {
  return (
    <div 
      className={clsx('clay-panel', className)} 
      {...props}
    >
      {children}
    </div>
  );
};
