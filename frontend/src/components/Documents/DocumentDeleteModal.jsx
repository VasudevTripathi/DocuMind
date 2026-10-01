import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { Button } from '../ui/Button';

export const DocumentDeleteModal = ({ isOpen, document, onClose, onConfirm, isDeleting }) => {
  if (!isOpen || !document) return null;

  return (
    <div 
      className="modal-backdrop"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(3, 3, 5, 0.8)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: 'var(--space-4)'
      }}
    >
      <div 
        className="delete-modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--bg-surface)',
          border: 'var(--border-glass)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-6)',
          maxWidth: '440px',
          width: '100%',
          boxShadow: 'var(--shadow-lg)',
          position: 'relative'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
          <div 
            style={{
              width: '42px',
              height: '42px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--danger-bg)',
              color: 'var(--danger)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}
          >
            <AlertTriangle size={22} />
          </div>
          <div style={{ flex: 1 }}>
            <h3 style={{ margin: '0 0 6px', fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--text-primary)' }}>
              Delete Document
            </h3>
            <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Are you sure you want to delete <strong style={{ color: 'var(--text-primary)' }}>{document.name}</strong>? This action cannot be undone.
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={isDeleting}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: isDeleting ? 'not-allowed' : 'pointer',
              padding: '4px',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center'
            }}
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-3)', marginTop: 'var(--space-6)' }}>
          <Button variant="secondary" onClick={onClose} disabled={isDeleting}>
            Cancel
          </Button>
          <Button 
            variant="danger" 
            onClick={() => onConfirm(document.id)}
            disabled={isDeleting}
          >
            {isDeleting ? 'Deleting...' : 'Delete Document'}
          </Button>
        </div>
      </div>
    </div>
  );
};
