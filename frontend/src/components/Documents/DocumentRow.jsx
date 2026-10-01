import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, Image as ImageIcon, MoreHorizontal, 
  ExternalLink, MessageSquare, Columns, Trash2 
} from 'lucide-react';
import { Badge } from '../ui/Badge';
import { documentService } from '../../services/documentService';

export const DocumentRow = ({ doc, onDeleteClick }) => {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) {
      document.addEventListener('click', handleOutsideClick);
    }
    return () => {
      document.removeEventListener('click', handleOutsideClick);
    };
  }, [menuOpen]);

  const handleRowClick = () => {
    navigate(`/workspace/${doc.id}`);
  };

  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case 'analyzed':
        return <Badge variant="success" icon="✓">Analyzed</Badge>;
      case 'processing':
        return <Badge variant="warning" icon="⟳">Processing</Badge>;
      case 'pending':
        return <Badge variant="default" icon="⏳">Pending</Badge>;
      case 'failed':
        return <Badge variant="danger" icon="✕">Failed</Badge>;
      default:
        return <Badge variant="default">{status || 'Unknown'}</Badge>;
    }
  };

  const getFileIcon = (doc) => {
    const type = (doc.type || documentService.getFileType(doc.name)).toUpperCase();
    if (type === 'IMAGE') {
      return <ImageIcon size={18} className="text-success" style={{ flexShrink: 0 }} />;
    }
    if (type === 'PDF') {
      return <FileText size={18} className="text-danger" style={{ flexShrink: 0 }} />;
    }
    if (type === 'PPT' || type === 'PPTX') {
      return <FileText size={18} className="text-warning" style={{ flexShrink: 0 }} />;
    }
    if (type === 'DOC' || type === 'DOCX') {
      return <FileText size={18} className="text-accent-secondary" style={{ flexShrink: 0 }} />;
    }
    return <FileText size={18} className="text-secondary" style={{ flexShrink: 0 }} />;
  };

  return (
    <tr 
      onClick={handleRowClick}
      className="cursor-pointer doc-table-row"
    >
      <td className="doc-name-cell">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', minWidth: 0 }}>
          {getFileIcon(doc)}
          <span 
            className="text-primary" 
            style={{ 
              fontWeight: 500, 
              overflow: 'hidden', 
              textOverflow: 'ellipsis', 
              whiteSpace: 'nowrap',
              maxWidth: '360px'
            }}
            title={doc.name}
          >
            {doc.name}
          </span>
        </div>
      </td>
      <td className="text-secondary">
        <span style={{ fontSize: 'var(--font-size-xs)', background: 'rgba(255, 255, 255, 0.05)', padding: '2px 8px', borderRadius: 'var(--radius-sm)' }}>
          {doc.type || documentService.getFileType(doc.name)}
        </span>
      </td>
      <td className="text-secondary" style={{ fontSize: 'var(--font-size-sm)', whiteSpace: 'nowrap' }}>
        {doc.size}
      </td>
      <td className="text-secondary" style={{ fontSize: 'var(--font-size-sm)', whiteSpace: 'nowrap' }}>
        {documentService.formatDate(doc.uploadedAt || doc.modifiedAt)}
      </td>
      <td>
        {getStatusBadge(doc.status)}
      </td>
      <td style={{ position: 'relative', textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
        <button
          className="action-btn text-secondary p-1 rounded hover:bg-white/10"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Document options"
          style={{
            padding: '6px',
            borderRadius: 'var(--radius-sm)',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: menuOpen ? 'var(--text-primary)' : 'var(--text-secondary)',
            background: menuOpen ? 'rgba(255, 255, 255, 0.1)' : 'transparent'
          }}
        >
          <MoreHorizontal size={16} />
        </button>

        {menuOpen && (
          <div 
            ref={menuRef}
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
              minWidth: '150px',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px'
            }}
          >
            <button
              className="doc-menu-item"
              onClick={() => {
                setMenuOpen(false);
                navigate(`/workspace/${doc.id}`);
              }}
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
            >
              <ExternalLink size={14} className="text-accent-primary" />
              <span>Open</span>
            </button>
            <button
              className="doc-menu-item"
              onClick={() => {
                setMenuOpen(false);
                navigate('/chat');
              }}
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
            >
              <MessageSquare size={14} className="text-accent-secondary" />
              <span>Ask AI</span>
            </button>
            <button
              className="doc-menu-item"
              onClick={() => {
                setMenuOpen(false);
                navigate('/compare');
              }}
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
            >
              <Columns size={14} className="text-success" />
              <span>Compare</span>
            </button>
            <div style={{ height: '1px', background: 'rgba(255, 255, 255, 0.06)', margin: '2px 0' }} />
            <button
              className="doc-menu-item text-danger"
              onClick={() => {
                setMenuOpen(false);
                onDeleteClick(doc);
              }}
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
            >
              <Trash2 size={14} />
              <span>Delete</span>
            </button>
          </div>
        )}
      </td>
    </tr>
  );
};
