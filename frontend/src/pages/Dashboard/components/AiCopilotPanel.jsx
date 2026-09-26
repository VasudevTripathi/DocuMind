import React, { useRef, useState } from 'react';
import { GlassPanel } from '../../../components/ui/GlassPanel';
import { Bot, FileText, X } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { useNavigate } from 'react-router-dom';

export const AiCopilotPanel = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
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
      setSelectedFile(file);
    }
  };

  const handleRemoveFile = (e) => {
    e.stopPropagation();
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
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
        onClick={handleUploadClick}
        style={{
          cursor: 'pointer',
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
              ({(selectedFile.size / 1024).toFixed(0)} KB)
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

        <Button 
          variant="primary"
          onClick={(e) => {
            e.stopPropagation();
            handleUploadClick();
          }}
        >
          {selectedFile ? 'Change Document' : 'Upload Document'}
        </Button>
      </div>
    </GlassPanel>
  );
};

