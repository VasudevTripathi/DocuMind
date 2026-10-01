import React, { useRef, useState } from 'react';
import { GlassPanel } from '../../../components/ui/GlassPanel';
import { Bot, FileText, X, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { useNavigate } from 'react-router-dom';
import { useDocuments } from '../../../hooks/useDocuments';
import { documentService } from '../../../services/documentService';

export const AiCopilotPanel = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();
  const { saveDocument } = useDocuments();

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const processFile = (file) => {
    setUploadError('');
    setUploadSuccess(false);
    if (!file) return;

    const validation = documentService.validateFile(file);
    if (!validation.valid) {
      setUploadError(validation.error);
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const handleRemoveFile = (e) => {
    e?.stopPropagation();
    setSelectedFile(null);
    setUploadError('');
    setUploadSuccess(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleConfirmUpload = async (e) => {
    e.stopPropagation();
    if (!selectedFile) {
      handleUploadClick();
      return;
    }

    setIsUploading(true);
    setUploadError('');

    try {
      const newDoc = documentService.createDocumentFromFile(selectedFile);
      await saveDocument(newDoc);
      setIsUploading(false);
      setUploadSuccess(true);
      setTimeout(() => {
        handleRemoveFile();
      }, 2000);
    } catch (err) {
      setIsUploading(false);
      setUploadError('Failed to upload document. Please try again.');
    }
  };

  return (
    <GlassPanel className="copilot-panel flex-row">
      <div className="copilot-info-area">
        <div className="copilot-header mb-4">
          <div className="copilot-icon-wrapper">
            <Bot size={24} className="text-accent-primary" />
          </div>
          <div className="copilot-title-area">
            <h3>DocuMind Copilot</h3>
            <p className="text-secondary text-sm">Get instant insights, summaries, answers and cross-document intelligence.</p>
          </div>
        </div>
        <div className="capability-chips flex flex-wrap gap-2 mt-4">
          <span className="ai-chip cursor-pointer" onClick={() => navigate('/documents')}>Summarize</span>
          <span className="ai-chip cursor-pointer" onClick={() => navigate('/chat')}>Ask Questions</span>
          <span className="ai-chip cursor-pointer" onClick={() => navigate('/documents')}>Extract Entities</span>
          <span className="ai-chip cursor-pointer" onClick={() => navigate('/compare')}>Compare</span>
          <span className="ai-chip cursor-pointer" onClick={() => navigate('/analytics')}>Generate Insights</span>
        </div>
      </div>
      
      <div 
        className={`dropzone-area premium-dropzone ${isDragging ? 'dragover' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={!selectedFile ? handleUploadClick : undefined}
        style={{
          cursor: selectedFile ? 'default' : 'pointer',
          borderColor: isDragging ? 'var(--accent-primary)' : undefined,
          background: isDragging ? 'rgba(123, 63, 228, 0.1)' : undefined,
          transition: 'all var(--transition-fast)'
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.ppt,.pptx,.png,.jpg,.jpeg"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <div className="dropzone-icon mb-2 text-accent-secondary">↑</div>
        <p className="dropzone-text font-medium text-lg">Drop your document here</p>
        
        {uploadError && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--danger)', fontSize: '11px', margin: '4px 0 10px', textAlign: 'center' }}>
            <AlertCircle size={14} />
            <span>{uploadError}</span>
          </div>
        )}

        {uploadSuccess && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--success)', fontSize: '11px', margin: '4px 0 10px' }}>
            <CheckCircle2 size={14} />
            <span>Document added to library!</span>
          </div>
        )}

        {selectedFile ? (
          <div 
            className="selected-file-state" 
            onClick={(e) => e.stopPropagation()}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px', 
              padding: '6px 12px', 
              background: 'rgba(123, 63, 228, 0.15)', 
              borderRadius: 'var(--radius-md)', 
              border: '1px solid rgba(123, 63, 228, 0.3)', 
              margin: '8px 0 16px', 
              maxWidth: '100%' 
            }}
          >
            <FileText size={16} className="text-accent-primary" style={{ flexShrink: 0 }} />
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '180px' }}>
              {selectedFile.name}
            </span>
            <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', flexShrink: 0 }}>
              ({documentService.formatFileSize(selectedFile.size)})
            </span>
            <button 
              type="button" 
              onClick={handleRemoveFile}
              style={{ 
                background: 'none', 
                border: 'none', 
                color: 'var(--text-tertiary)', 
                cursor: 'pointer', 
                padding: '0 2px', 
                display: 'flex', 
                alignItems: 'center' 
              }}
              title="Remove file"
            >
              <X size={14} />
            </button>
          </div>
        ) : (
          <p className="dropzone-subtext text-tertiary text-sm mb-4">PDF, DOCX, TXT, PPT, Images</p>
        )}

        <div style={{ display: 'flex', gap: '8px', width: '100%', justifyContent: 'center' }}>
          {selectedFile ? (
            <>
              <Button 
                variant="secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  handleUploadClick();
                }}
                disabled={isUploading}
              >
                Change
              </Button>
              <Button 
                variant="primary"
                onClick={handleConfirmUpload}
                disabled={isUploading}
              >
                {isUploading ? 'Uploading...' : 'Upload & Process'}
              </Button>
            </>
          ) : (
            <Button 
              variant="primary"
              onClick={(e) => {
                e.stopPropagation();
                handleUploadClick();
              }}
            >
              Upload Document
            </Button>
          )}
        </div>
      </div>
    </GlassPanel>
  );
};
