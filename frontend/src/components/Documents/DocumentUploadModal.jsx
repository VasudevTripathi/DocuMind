import React, { useState, useRef } from 'react';
import { Upload, X, FileText, Image as ImageIcon, AlertCircle, CheckCircle2 } from 'lucide-react';
import { GlassPanel } from '../ui/GlassPanel';
import { Button } from '../ui/Button';
import { documentService } from '../../services/documentService';

export const DocumentUploadModal = ({ isOpen, onClose, onUploadSuccess }) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [category, setCategory] = useState('General');
  const [validationError, setValidationError] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef(null);
  const uploadTimerRef = useRef(null);

  if (!isOpen) return null;

  const resetState = () => {
    if (uploadTimerRef.current) {
      clearInterval(uploadTimerRef.current);
    }
    setSelectedFile(null);
    setValidationError('');
    setIsUploading(false);
    setUploadProgress(0);
    setCategory('General');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    if (isUploading) {
      const confirmCancel = window.confirm('Upload is in progress. Are you sure you want to cancel?');
      if (!confirmCancel) return;
    }
    resetState();
    onClose();
  };

  const handleFile = (file) => {
    setValidationError('');
    if (!file) return;

    const validation = documentService.validateFile(file);
    if (!validation.valid) {
      setValidationError(validation.error);
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    // Suggest category based on filename or type
    const nameLower = file.name.toLowerCase();
    if (nameLower.includes('paper') || nameLower.includes('thesis') || nameLower.includes('study')) {
      setCategory('Research Paper');
    } else if (nameLower.includes('report') || nameLower.includes('annual') || nameLower.includes('q1') || nameLower.includes('q2')) {
      setCategory('Business Report');
    } else if (nameLower.includes('contract') || nameLower.includes('agreement') || nameLower.includes('nda')) {
      setCategory('Legal');
    } else if (nameLower.includes('spec') || nameLower.includes('tech') || nameLower.includes('architecture')) {
      setCategory('Technical');
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const startUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadProgress(10);

    // Simulate transfer progress (uploading data)
    let progress = 10;
    uploadTimerRef.current = setInterval(async () => {
      progress += Math.floor(Math.random() * 25) + 15;
      if (progress >= 100) {
        clearInterval(uploadTimerRef.current);
        setUploadProgress(100);

        try {
          const newDoc = documentService.createDocumentFromFile(selectedFile, category);
          await onUploadSuccess(newDoc);
          setTimeout(() => {
            resetState();
            onClose();
          }, 350);
        } catch (err) {
          setValidationError('Failed to save document. Please try again.');
          setIsUploading(false);
        }
      } else {
        setUploadProgress(progress);
      }
    }, 120);
  };

  const getFileIcon = (fileName) => {
    const type = documentService.getFileType(fileName);
    if (type === 'Image') return <ImageIcon size={24} className="text-success" />;
    if (type === 'PDF') return <FileText size={24} className="text-danger" />;
    return <FileText size={24} className="text-accent-primary" />;
  };

  return (
    <div 
      className="modal-backdrop"
      onClick={handleClose}
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
        className="upload-modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--bg-surface)',
          border: 'var(--border-glass)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-6)',
          maxWidth: '520px',
          width: '100%',
          boxShadow: 'var(--shadow-lg)',
          position: 'relative'
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--text-primary)' }}>
              Upload Document
            </h3>
            <p style={{ margin: '4px 0 0', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
              Add a document to your intelligent library
            </p>
          </div>
          <button
            onClick={handleClose}
            disabled={isUploading && uploadProgress < 100}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: isUploading ? 'not-allowed' : 'pointer',
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center'
            }}
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Drag and Drop Zone */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => !isUploading && fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragActive ? 'var(--accent-primary)' : 'rgba(255, 255, 255, 0.15)'}`,
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-6)',
            textAlign: 'center',
            backgroundColor: dragActive ? 'rgba(123, 63, 228, 0.08)' : 'rgba(255, 255, 255, 0.02)',
            cursor: isUploading ? 'default' : 'pointer',
            transition: 'all var(--transition-fast)',
            marginBottom: 'var(--space-4)'
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.doc,.docx,.txt,.ppt,.pptx,.png,.jpg,.jpeg"
            style={{ display: 'none' }}
            onChange={handleFileInputChange}
            disabled={isUploading}
          />
          <div 
            style={{
              width: '48px',
              height: '48px',
              borderRadius: 'var(--radius-full)',
              background: 'rgba(123, 63, 228, 0.15)',
              color: 'var(--accent-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto var(--space-3)'
            }}
          >
            <Upload size={22} />
          </div>
          <p style={{ margin: '0 0 6px', fontWeight: 500, color: 'var(--text-primary)', fontSize: 'var(--font-size-sm)' }}>
            Click to browse or drag & drop your document
          </p>
          <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-tertiary)' }}>
            PDF, DOCX, TXT, PPT, Images up to 50MB
          </p>
        </div>

        {/* Validation Error Alert */}
        {validationError && (
          <div 
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              padding: 'var(--space-3)',
              borderRadius: 'var(--radius-md)',
              background: 'var(--danger-bg)',
              color: 'var(--danger)',
              fontSize: 'var(--font-size-xs)',
              marginBottom: 'var(--space-4)'
            }}
          >
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{validationError}</span>
          </div>
        )}

        {/* Selected File Details */}
        {selectedFile && !validationError && (
          <div 
            style={{
              padding: 'var(--space-3) var(--space-4)',
              background: 'rgba(255, 255, 255, 0.04)',
              border: 'var(--border-glass)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-4)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-3)'
            }}
          >
            <div style={{ flexShrink: 0 }}>
              {getFileIcon(selectedFile.name)}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {selectedFile.name}
              </p>
              <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
                {documentService.formatFileSize(selectedFile.size)} • {documentService.getFileType(selectedFile.name)}
              </p>
            </div>
            {!isUploading && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-tertiary)',
                  cursor: 'pointer',
                  padding: '4px'
                }}
                title="Remove file"
              >
                <X size={16} />
              </button>
            )}
          </div>
        )}

        {/* Category Selection */}
        {selectedFile && !validationError && !isUploading && (
          <div style={{ marginBottom: 'var(--space-5)' }}>
            <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginBottom: 'var(--space-2)' }}>
              Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={{
                width: '100%',
                padding: 'var(--space-2) var(--space-3)',
                background: 'rgba(255, 255, 255, 0.05)',
                border: 'var(--border-glass)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-primary)',
                fontSize: 'var(--font-size-sm)',
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              <option value="General" style={{ background: '#0a0a0f', color: '#fff' }}>General</option>
              <option value="Research Paper" style={{ background: '#0a0a0f', color: '#fff' }}>Research Paper</option>
              <option value="Business Report" style={{ background: '#0a0a0f', color: '#fff' }}>Business Report</option>
              <option value="Technical" style={{ background: '#0a0a0f', color: '#fff' }}>Technical Specification</option>
              <option value="Legal" style={{ background: '#0a0a0f', color: '#fff' }}>Legal & Contract</option>
            </select>
          </div>
        )}

        {/* Upload Progress Bar */}
        {isUploading && (
          <div style={{ marginBottom: 'var(--space-5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', marginBottom: 'var(--space-2)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>
                {uploadProgress < 100 ? 'Uploading document...' : 'Finalizing & queuing for processing...'}
              </span>
              <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{uploadProgress}%</span>
            </div>
            <div style={{ height: '6px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
              <div 
                style={{
                  height: '100%',
                  width: `${uploadProgress}%`,
                  background: 'linear-gradient(90deg, var(--accent-secondary), var(--accent-primary))',
                  transition: 'width 0.2s ease-out'
                }}
              />
            </div>
          </div>
        )}

        {/* Modal Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-3)' }}>
          <Button 
            variant="secondary" 
            onClick={handleClose}
            disabled={isUploading && uploadProgress < 100}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={startUpload}
            disabled={!selectedFile || Boolean(validationError) || isUploading}
          >
            {isUploading ? 'Uploading...' : 'Upload Document'}
          </Button>
        </div>
      </div>
    </div>
  );
};
