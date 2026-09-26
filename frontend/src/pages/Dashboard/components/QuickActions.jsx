import React from 'react';
import { GlassPanel } from '../../../components/ui/GlassPanel';
import { FileText, HelpCircle, Columns, Network, Table } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const QuickActions = () => {
  const navigate = useNavigate();

  const actions = [
    { icon: FileText, label: 'Summarize a document', color: 'text-accent-primary', path: '/documents' },
    { icon: HelpCircle, label: 'Ask a question', color: 'text-accent-secondary', path: '/chat' },
    { icon: Columns, label: 'Compare documents', color: 'text-success', path: '/compare' },
    { icon: Network, label: 'Generate mind map', color: 'text-warning', path: '/chat' },
    { icon: Table, label: 'Extract data (tables)', color: 'text-danger', path: '/documents' },
  ];

  return (
    <div className="quick-actions-section">
      <h3 className="section-title mb-4">Quick Actions</h3>
      <div className="quick-actions-list flex flex-col gap-2">
        {actions.map((action, idx) => (
          <GlassPanel 
            key={idx} 
            className="quick-action-item cursor-pointer"
            onClick={() => navigate(action.path)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                navigate(action.path);
              }
            }}
          >
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
