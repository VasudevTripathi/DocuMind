import React from 'react';
import { GlassPanel } from '../../../components/ui/GlassPanel';
import { Badge } from '../../../components/ui/Badge';
import { FileText, MoreHorizontal, ArrowRight } from 'lucide-react';

export const RecentDocuments = () => {
  const docs = [
    { name: 'Attention Is All You Need.pdf', type: 'Research Paper', size: '2.4 MB', time: '2 hours ago', status: 'Analyzed', statusColor: 'success' },
    { name: 'Annual Report 2023.pdf', type: 'Business Report', size: '4.1 MB', time: '1 day ago', status: 'Analyzed', statusColor: 'success' },
    { name: 'Technical Specification.docx', type: 'Technical', size: '1.2 MB', time: '3 days ago', status: 'Processing', statusColor: 'warning' },
    { name: 'Contract Agreement.pdf', type: 'Legal', size: '3.8 MB', time: '5 days ago', status: 'Analyzed', statusColor: 'success' },
  ];

  return (
    <div className="recent-docs-section">
      <div className="section-header">
        <h3>Recent Documents</h3>
        <button className="view-all-btn text-accent-primary">
          View all <ArrowRight size={14} />
        </button>
      </div>

      <GlassPanel className="table-container p-0">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Size</th>
              <th>Modified</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {docs.map((doc, idx) => (
              <tr key={idx}>
                <td className="doc-name-cell">
                  <FileText size={16} className={doc.name.endsWith('pdf') ? 'text-danger' : 'text-accent-secondary'} />
                  <span className="text-primary">{doc.name}</span>
                </td>
                <td className="text-secondary">{doc.type}</td>
                <td className="text-secondary">{doc.size}</td>
                <td className="text-secondary">{doc.time}</td>
                <td>
                  <Badge variant={doc.statusColor} icon={doc.status === 'Analyzed' ? '✓' : '⟳'}>
                    {doc.status}
                  </Badge>
                </td>
                <td>
                  <button className="action-btn text-secondary"><MoreHorizontal size={16} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </GlassPanel>
    </div>
  );
};
