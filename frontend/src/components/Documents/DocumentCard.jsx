import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, Image as ImageIcon, 
  ExternalLink, MessageSquare, Columns, Trash2 
} from 'lucide-react';
import { GlassPanel } from '../ui/GlassPanel';
import { Badge } from '../ui/Badge';
import { documentService } from '../../services/documentService';

export const DocumentCard = ({ doc, onDeleteClick }) => {
  const navigate = useNavigate();

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
    if (type === 'IMAGE') {
      return <ImageIcon size={22} className="text-success" style={{ flexShrink: 0 }} />;
    }
    if (type === 'PDF') {
      return <FileText size={22} className="text-danger" style={{ flexShrink: 0 }} />;
    }
    if (type === 'PPT' || type === 'PPTX') {
      return <FileText size={22} className="text-warning" style={{ flexShrink: 0 }} />;
    }
    if (type === 'DOC' || type === 'DOCX') {
      return <FileText size={22} className="text-accent-secondary" style={{ flexShrink: 0 }} />;
    }
    return <FileText size={22} className="text-secondary" style={{ flexShrink: 0 }} />;
  };

  return (
    <GlassPanel 
      className="doc-card"
      onClick={() => navigate(`/workspace/${doc.id}`)}
      style={{
        padding: 'var(--space-4)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-3)',
        cursor: 'pointer',
        transition: 'all var(--transition-fast)',
        border: 'var(--border-glass)'
      }}
    >
      {/* Top Header: Icon + Name + Status */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', minWidth: 0, flex: 1 }}>
          <div 
            style={{ 
              width: '38px', 
              height: '38px', 
              borderRadius: 'var(--radius-sm)', 
              background: 'rgba(255, 255, 255, 0.05)', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              flexShrink: 0 
            }}
          >
            {getFileIcon(doc)}
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <h4 
              style={{ 
                margin: 0, 
                fontSize: 'var(--font-size-sm)', 
                fontWeight: 600, 
                color: 'var(--text-primary)', 
                overflow: 'hidden', 
                textOverflow: 'ellipsis', 
                whiteSpace: 'nowrap' 
              }}
              title={doc.name}
            >
              {doc.name}
            </h4>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginTop: '2px', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
              <span>{doc.type || documentService.getFileType(doc.name)}</span>
              <span>•</span>
              <span>{doc.size}</span>
            </div>
          </div>
        </div>
        <div style={{ flexShrink: 0 }}>
          {getStatusBadge(doc.status)}
        </div>
      </div>

      {/* Meta info & Action Buttons */}
      <div 
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between', 
          paddingTop: 'var(--space-2)', 
          borderTop: '1px solid rgba(255, 255, 255, 0.05)' 
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
          {documentService.formatDate(doc.uploadedAt || doc.modifiedAt)}
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <button
            onClick={() => navigate(`/workspace/${doc.id}`)}
            className="card-action-btn"
            title="Open workspace"
            style={{
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-secondary)',
              background: 'rgba(255, 255, 255, 0.05)',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <ExternalLink size={14} />
          </button>
          <button
            onClick={() => navigate('/chat')}
            className="card-action-btn"
            title="Ask AI"
            style={{
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--accent-secondary)',
              background: 'rgba(255, 255, 255, 0.05)',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <MessageSquare size={14} />
          </button>
          <button
            onClick={() => navigate('/compare')}
            className="card-action-btn"
            title="Compare"
            style={{
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--success)',
              background: 'rgba(255, 255, 255, 0.05)',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <Columns size={14} />
          </button>
          <button
            onClick={() => onDeleteClick(doc)}
            className="card-action-btn text-danger"
            title="Delete document"
            style={{
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--danger)',
              background: 'rgba(239, 68, 68, 0.1)',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </GlassPanel>
  );
};
