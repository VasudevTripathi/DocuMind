import React from 'react';
import { clsx } from 'clsx';
import './ui.css';

export const Button = ({ children, variant = 'primary', className, ...props }) => {
  return (
    <button 
      className={clsx('btn', `btn-${variant}`, className)} 
      {...props}
    >
      {children}
    </button>
  );
};
