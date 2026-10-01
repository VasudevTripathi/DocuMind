import React, { useState } from 'react';
import { GlassPanel } from '../../../components/ui/GlassPanel';
import { Badge } from '../../../components/ui/Badge';
import { FileText, MoreHorizontal, ArrowRight, Image as ImageIcon, ExternalLink, MessageSquare, Columns, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useDocuments } from '../../../hooks/useDocuments';
import { documentService } from '../../../services/documentService';
import { DocumentSkeleton } from '../../../components/Documents/DocumentSkeleton';
import { DocumentDeleteModal } from '../../../components/Documents/DocumentDeleteModal';

export const RecentDocuments = () => {
  const navigate = useNavigate();
  const { documents, isLoading, deleteDocument, isDeleting } = useDocuments();
  const [openMenuIdx, setOpenMenuIdx] = useState(null);
  const [docToDelete, setDocToDelete] = useState(null);

  // Take the most recent 4 documents
  const recentDocs = documents.slice(0, 4);

  const handleRowClick = (id) => {
    navigate(`/workspace/${id}`);
  };

  const toggleMenu = (e, idx) => {
    e.stopPropagation();
    setOpenMenuIdx(openMenuIdx === idx ? null : idx);
  };

  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case 'analyzed':
        return <Badge variant="success" icon="✓">Analyzed</Badge>;
      case 'processing':
        return <Badge variant="warning" icon="⟳">Processing</Badge>;
      case 'failed':
        return <Badge variant="danger" icon="✕">Failed</Badge>;
      default:
        return <Badge variant="default">{status || 'Unknown'}</Badge>;
    }
  };

  const getFileIcon = (doc) => {
    const type = (doc.type || documentService.getFileType(doc.name)).toUpperCase();
    if (type === 'IMAGE') return <ImageIcon size={16} className="text-success" />;
    if (type === 'PDF') return <FileText size={16} className="text-danger" />;
    if (type === 'DOC' || type === 'DOCX') return <FileText size={16} className="text-accent-secondary" />;
    if (type === 'PPT' || type === 'PPTX') return <FileText size={16} className="text-warning" />;
    return <FileText size={16} className="text-secondary" />;
  };

  const handleDeleteConfirm = async (id) => {
    try {
      await deleteDocument(id);
      setDocToDelete(null);
    } catch (err) {
      console.error('Failed to delete document from dashboard:', err);
    }
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
              <th style={{ textAlign: 'right' }}></th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <DocumentSkeleton count={3} />
            ) : recentDocs.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--text-secondary)' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                    <p style={{ margin: 0, fontSize: 'var(--font-size-sm)' }}>No documents in your library yet.</p>
                    <button 
                      onClick={() => navigate('/documents')}
                      className="text-accent-primary"
                      style={{ fontSize: 'var(--font-size-xs)', textDecoration: 'underline', cursor: 'pointer' }}
                    >
                      Upload your first document
                    </button>
                  </div>
                </td>
              </tr>
            ) : (
              recentDocs.map((doc, idx) => (
                <tr key={doc.id || idx} onClick={() => handleRowClick(doc.id)} className="cursor-pointer">
                  <td className="doc-name-cell">
                    {getFileIcon(doc)}
                    <span 
                      className="text-primary"
                      style={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: '280px'
                      }}
                      title={doc.name}
                    >
                      {doc.name}
                    </span>
                  </td>
                  <td className="text-secondary">{doc.type || documentService.getFileType(doc.name)}</td>
                  <td className="text-secondary">{doc.size}</td>
                  <td className="text-secondary">{documentService.formatDate(doc.uploadedAt || doc.modifiedAt)}</td>
                  <td>
                    {getStatusBadge(doc.status)}
                  </td>
                  <td style={{ position: 'relative', textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                    <button 
                      className="action-btn text-secondary p-1 rounded hover:bg-white/10" 
                      onClick={(e) => toggleMenu(e, idx)}
                      aria-label="Actions"
                    >
                      <MoreHorizontal size={16} />
                    </button>
                    {openMenuIdx === idx && (
                      <div 
                        className="doc-action-menu"
                        style={{
                          position: 'absolute',
                          right: '8px',
                          top: '100%',
                          marginTop: '4px',
                          background: 'var(--bg-surface)',
                          border: 'var(--border-glass)',
                          borderRadius: 'var(--radius-md)',
                          boxShadow: 'var(--shadow-lg)',
                          padding: '4px',
                          zIndex: 50,
                          minWidth: '140px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '2px'
                        }}
                      >
                        <button 
                          className="doc-menu-item"
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 'var(--space-2)',
                            padding: '6px 12px',
                            fontSize: 'var(--font-size-xs)',
                            color: 'var(--text-primary)',
                            borderRadius: 'var(--radius-sm)',
                            textAlign: 'left',
                            width: '100%'
                          }}
                          onClick={() => { setOpenMenuIdx(null); navigate(`/workspace/${doc.id}`); }}
                        >
                          <ExternalLink size={14} className="text-accent-primary" />
                          <span>Open</span>
                        </button>
                        <button 
                          className="doc-menu-item"
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 'var(--space-2)',
                            padding: '6px 12px',
                            fontSize: 'var(--font-size-xs)',
                            color: 'var(--text-primary)',
                            borderRadius: 'var(--radius-sm)',
                            textAlign: 'left',
                            width: '100%'
                          }}
                          onClick={() => { setOpenMenuIdx(null); navigate('/chat'); }}
                        >
                          <MessageSquare size={14} className="text-accent-secondary" />
                          <span>Ask AI</span>
                        </button>
                        <button 
                          className="doc-menu-item"
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 'var(--space-2)',
                            padding: '6px 12px',
                            fontSize: 'var(--font-size-xs)',
                            color: 'var(--text-primary)',
                            borderRadius: 'var(--radius-sm)',
                            textAlign: 'left',
                            width: '100%'
                          }}
                          onClick={() => { setOpenMenuIdx(null); navigate('/compare'); }}
                        >
                          <Columns size={14} className="text-success" />
                          <span>Compare</span>
                        </button>
                        <div style={{ height: '1px', background: 'rgba(255, 255, 255, 0.06)', margin: '2px 0' }} />
                        <button 
                          className="doc-menu-item text-danger"
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 'var(--space-2)',
                            padding: '6px 12px',
                            fontSize: 'var(--font-size-xs)',
                            color: 'var(--danger)',
                            borderRadius: 'var(--radius-sm)',
                            textAlign: 'left',
                            width: '100%'
                          }}
                          onClick={() => { 
                            setOpenMenuIdx(null); 
                            setDocToDelete(doc); 
                          }}
                        >
                          <Trash2 size={14} />
                          <span>Delete</span>
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </GlassPanel>

      {/* Delete Confirmation Modal */}
      <DocumentDeleteModal
        isOpen={Boolean(docToDelete)}
        document={docToDelete}
        onClose={() => setDocToDelete(null)}
        onConfirm={handleDeleteConfirm}
        isDeleting={isDeleting}
      />
    </div>
  );
};
