import React from 'react';
import { GlassPanel } from '../../../components/ui/GlassPanel';
import { FileText, HelpCircle, Columns, Network, Table } from 'lucide-react';

export const QuickActions = () => {
  const actions = [
    { icon: FileText, label: 'Summarize a document', color: 'text-accent-primary' },
    { icon: HelpCircle, label: 'Ask a question', color: 'text-accent-secondary' },
    { icon: Columns, label: 'Compare documents', color: 'text-success' },
    { icon: Network, label: 'Generate mind map', color: 'text-warning' },
    { icon: Table, label: 'Extract data (tables)', color: 'text-danger' },
  ];

  return (
    <div className="quick-actions-section">
      <h3 className="section-title mb-4">Quick Actions</h3>
      <div className="quick-actions-list flex flex-col gap-2">
        {actions.map((action, idx) => (
          <GlassPanel key={idx} className="quick-action-item">
            <div className={`action-icon-bg ${action.color}`}>
              <action.icon size={16} />
            </div>
            <span className="text-sm font-medium">{action.label}</span>
          </GlassPanel>
        ))}
      </div>
      
      <GlassPanel className="quote-panel mt-4">
        <h4 className="text-xs text-secondary mb-2 uppercase tracking-wider">Today's Quote</h4>
        <p className="text-sm italic text-primary">"A document is a dialogue between the past and the future."</p>
        <p className="text-xs text-tertiary mt-2">— Unknown</p>
      </GlassPanel>
    </div>
  );
};
