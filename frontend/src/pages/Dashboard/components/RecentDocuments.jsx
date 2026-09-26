import React, { useState } from 'react';
import { GlassPanel } from '../../../components/ui/GlassPanel';
import { Badge } from '../../../components/ui/Badge';
import { FileText, MoreHorizontal, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const RecentDocuments = () => {
  const navigate = useNavigate();
  const [openMenuIdx, setOpenMenuIdx] = useState(null);

  const docs = [
    { id: '1', name: 'Attention Is All You Need.pdf', type: 'Research Paper', size: '2.4 MB', time: '2 hours ago', status: 'Analyzed', statusColor: 'success' },
    { id: '2', name: 'Annual Report 2023.pdf', type: 'Business Report', size: '4.1 MB', time: '1 day ago', status: 'Analyzed', statusColor: 'success' },
    { id: '3', name: 'Technical Specification.docx', type: 'Technical', size: '1.2 MB', time: '3 days ago', status: 'Processing', statusColor: 'warning' },
    { id: '4', name: 'Contract Agreement.pdf', type: 'Legal', size: '3.8 MB', time: '5 days ago', status: 'Analyzed', statusColor: 'success' },
  ];

  const handleRowClick = (id) => {
    navigate(`/workspace/${id}`);
  };

  const toggleMenu = (e, idx) => {
    e.stopPropagation();
    setOpenMenuIdx(openMenuIdx === idx ? null : idx);
  };

  return (
    <div className="recent-docs-section">
      <div className="section-header">
        <h3>Recent Documents</h3>
        <button className="view-all-btn text-accent-primary" onClick={() => navigate('/documents')}>
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
              <tr key={idx} onClick={() => handleRowClick(doc.id)} className="cursor-pointer">
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
                <td style={{ position: 'relative' }}>
                  <button className="action-btn text-secondary p-1 rounded hover:bg-white/10" onClick={(e) => toggleMenu(e, idx)}>
                    <MoreHorizontal size={16} />
                  </button>
                  {openMenuIdx === idx && (
                    <div className="absolute right-8 top-8 bg-surface border border-glass rounded-md shadow-lg p-1 z-10 min-w-[120px] flex flex-col doc-action-menu">
                      <button 
                        className="text-left px-3 py-1.5 text-sm hover:bg-white/5 rounded"
                        onClick={(e) => { e.stopPropagation(); navigate(`/workspace/${doc.id}`); setOpenMenuIdx(null); }}
                      >
                        Open
                      </button>
                      <button 
                        className="text-left px-3 py-1.5 text-sm hover:bg-white/5 rounded"
                        onClick={(e) => { e.stopPropagation(); navigate('/chat'); setOpenMenuIdx(null); }}
                      >
                        Ask AI
                      </button>
                      <button 
                        className="text-left px-3 py-1.5 text-sm hover:bg-white/5 rounded"
                        onClick={(e) => { e.stopPropagation(); navigate('/compare'); setOpenMenuIdx(null); }}
                      >
                        Compare
                      </button>
                      <button 
                        className="text-left px-3 py-1.5 text-sm hover:bg-white/5 rounded text-danger"
                        onClick={(e) => { e.stopPropagation(); setOpenMenuIdx(null); }}
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </GlassPanel>
    </div>
  );
};
