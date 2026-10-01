import React, { useState, useMemo } from 'react';
import { 
  FileText, Search, Plus, X, AlertCircle, RefreshCw, 
  Filter, UploadCloud, CheckCircle2 
} from 'lucide-react';
import { GlassPanel } from '../../components/ui/GlassPanel';
import { Button } from '../../components/ui/Button';
import { useDocuments } from '../../hooks/useDocuments';
import { DocumentRow } from '../../components/Documents/DocumentRow';
import { DocumentCard } from '../../components/Documents/DocumentCard';
import { DocumentSkeleton } from '../../components/Documents/DocumentSkeleton';
import { DocumentUploadModal } from '../../components/Documents/DocumentUploadModal';
import { DocumentDeleteModal } from '../../components/Documents/DocumentDeleteModal';
import './Documents.css';

const TYPE_FILTERS = [
  { label: 'All', value: 'all' },
  { label: 'PDF', value: 'pdf' },
  { label: 'DOCX', value: 'docx' },
  { label: 'TXT', value: 'txt' },
  { label: 'PPT/PPTX', value: 'ppt' },
  { label: 'Images', value: 'image' }
];

export const Documents = () => {
  const {
    documents,
    isLoading,
    isError,
    error,
    refetch,
    saveDocument,
    deleteDocument,
    isDeleting
  } = useDocuments();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState(null);

  // Filter & Search logic
  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      // 1. Search Query filter (by name)
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const matchesName = doc.name.toLowerCase().includes(query);
        const matchesCategory = doc.category?.toLowerCase().includes(query);
        if (!matchesName && !matchesCategory) return false;
      }

      // 2. Type filter
      if (selectedType !== 'all') {
        const docType = (doc.type || '').toLowerCase();
        const docName = (doc.name || '').toLowerCase();

        if (selectedType === 'pdf') {
          if (docType !== 'pdf' && !docName.endsWith('.pdf')) return false;
        } else if (selectedType === 'docx') {
          if (docType !== 'docx' && docType !== 'doc' && !docName.endsWith('.docx') && !docName.endsWith('.doc')) return false;
        } else if (selectedType === 'txt') {
          if (docType !== 'txt' && !docName.endsWith('.txt')) return false;
        } else if (selectedType === 'ppt') {
          if (docType !== 'ppt' && docType !== 'pptx' && !docName.endsWith('.ppt') && !docName.endsWith('.pptx')) return false;
        } else if (selectedType === 'image') {
          const isImg = docType === 'image' || ['png', 'jpg', 'jpeg'].some(ext => docName.endsWith('.' + ext));
          if (!isImg) return false;
        }
      }

      // 3. Status filter
      if (selectedStatus !== 'all') {
        if ((doc.status || '').toLowerCase() !== selectedStatus.toLowerCase()) {
          return false;
        }
      }

      return true;
    });
  }, [documents, searchQuery, selectedType, selectedStatus]);

  const handleUploadSuccess = async (newDoc) => {
    await saveDocument(newDoc);
  };

  const handleDeleteConfirm = async (id) => {
    try {
      await deleteDocument(id);
      setDocToDelete(null);
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setSelectedType('all');
    setSelectedStatus('all');
  };

  const hasActiveFilters = searchQuery.trim() !== '' || selectedType !== 'all' || selectedStatus !== 'all';

  return (
    <div className="documents-container">
      {/* Header */}
      <div className="documents-header">
        <div className="documents-header-left">
          <h1>Documents</h1>
          <p className="text-secondary text-sm">
            Manage, search, and organize your document library.
          </p>
        </div>
        <Button 
          variant="primary" 
          onClick={() => setIsUploadOpen(true)}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)' }}
        >
          <Plus size={16} />
          <span>Upload Document</span>
        </Button>
      </div>

      {/* Toolbar: Search and Filter Groups */}
      <div className="documents-toolbar">
        <div className="toolbar-controls">
          {/* Search Input styled like TopNavbar */}
          <div className="doc-search-wrapper">
            <div className="doc-search-bar">
              <Search size={16} className="doc-search-icon" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents by filename..."
                className="doc-search-input"
              />
              {searchQuery && (
                <button 
                  type="button" 
                  onClick={() => setSearchQuery('')}
                  className="search-clear-btn"
                  title="Clear search"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          </div>

          {/* Status Dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="status-filter-select"
            >
              <option value="all">All Statuses</option>
              <option value="analyzed">Analyzed</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        {/* Type Pills */}
        <div className="filter-groups-wrapper">
          <div className="filter-pills-row">
            {TYPE_FILTERS.map((filter) => (
              <button
                key={filter.value}
                type="button"
                className={`filter-pill ${selectedType === filter.value ? 'active' : ''}`}
                onClick={() => setSelectedType(filter.value)}
              >
                {filter.label}
              </button>
            ))}
          </div>

          {/* Counts & Clear Filters */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <span className="documents-meta-count">
              Showing {filteredDocuments.length} of {documents.length} {documents.length === 1 ? 'document' : 'documents'}
            </span>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={handleClearFilters}
                style={{
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--accent-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                Clear filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <>
          <div className="desktop-table-view">
            <GlassPanel className="table-container p-0">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Uploaded</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <DocumentSkeleton count={4} isMobile={false} />
                </tbody>
              </table>
            </GlassPanel>
          </div>
          <div className="mobile-cards-view">
            <DocumentSkeleton count={4} isMobile={true} />
          </div>
        </>
      ) : isError ? (
        <GlassPanel className="documents-error-state">
          <AlertCircle size={32} className="text-danger" />
          <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>Failed to load documents</h3>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
            {error?.message || 'An error occurred while loading your document library.'}
          </p>
          <Button 
            variant="secondary" 
            onClick={() => refetch()} 
            style={{ marginTop: 'var(--space-2)', display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)' }}
          >
            <RefreshCw size={14} />
            <span>Retry</span>
          </Button>
        </GlassPanel>
      ) : documents.length === 0 ? (
        /* Empty Library State */
        <GlassPanel className="documents-empty-state">
          <div className="empty-state-icon-box">
            <FileText size={28} />
          </div>
          <h3 className="empty-state-title">No documents yet</h3>
          <p className="empty-state-subtitle">
            Upload your first document to start analyzing it with AI insights, summaries, and semantic search.
          </p>
          <Button variant="primary" onClick={() => setIsUploadOpen(true)}>
            <Plus size={16} />
            <span>Upload Document</span>
          </Button>
        </GlassPanel>
      ) : filteredDocuments.length === 0 ? (
        /* Empty Filter/Search State */
        <GlassPanel className="documents-empty-state">
          <div className="empty-state-icon-box" style={{ background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-secondary)' }}>
            <Search size={28} />
          </div>
          <h3 className="empty-state-title">No matching documents</h3>
          <p className="empty-state-subtitle">
            We couldn't find any documents matching your current search or filter criteria.
          </p>
          <Button variant="secondary" onClick={handleClearFilters}>
            Clear filters & search
          </Button>
        </GlassPanel>
      ) : (
        /* Document List: Desktop Table & Mobile Cards */
        <>
          <div className="desktop-table-view">
            <GlassPanel className="table-container p-0">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Uploaded</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDocuments.map((doc) => (
                    <DocumentRow 
                      key={doc.id} 
                      doc={doc} 
                      onDeleteClick={(d) => setDocToDelete(d)} 
                    />
                  ))}
                </tbody>
              </table>
            </GlassPanel>
          </div>

          <div className="mobile-cards-view">
            {filteredDocuments.map((doc) => (
              <DocumentCard 
                key={doc.id} 
                doc={doc} 
                onDeleteClick={(d) => setDocToDelete(d)} 
              />
            ))}
          </div>
        </>
      )}

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />

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
