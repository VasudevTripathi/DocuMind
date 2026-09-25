import React from 'react';
import { GlassPanel } from '../components/ui/GlassPanel';
import { Bot } from 'lucide-react';

export const Placeholder = ({ title }) => {
  return (
    <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <GlassPanel style={{ textAlign: 'center', padding: '48px', maxWidth: '400px' }}>
        <Bot size={48} className="text-accent-primary" style={{ margin: '0 auto 16px' }} />
        <h2 style={{ marginBottom: '8px' }}>{title}</h2>
        <p className="text-secondary">This module will be implemented in a subsequent phase.</p>
      </GlassPanel>
    </div>
  );
};
