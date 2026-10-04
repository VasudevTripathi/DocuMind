import React, { useState } from 'react';
import { FileText, ChevronDown, ChevronUp, Layers, Hash } from 'lucide-react';
import './SourceEvidence.css';

export const SourceEvidence = ({ sources = [], label = 'Source Evidence', variant = 'default' }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className={`source-evidence-wrapper source-variant-${variant}`}>
      <button 
        type="button"
        className="source-evidence-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
      >
        <span className="source-toggle-left">
          <FileText size={14} className="source-icon" />
          <span className="source-label">{label}</span>
          <span className="source-count-badge">{sources.length}</span>
        </span>
        <span className="source-toggle-right">
          <span className="source-hint">{isExpanded ? 'Hide' : 'Inspect'}</span>
          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </span>
      </button>

      {isExpanded && (
        <div className="source-evidence-content">
          {sources.map((src, idx) => (
            <div key={src.chunk_id || `${src.document_id}-${idx}`} className="source-chunk-card">
              <div className="source-chunk-header">
                <div className="source-chunk-doc">
                  <FileText size={13} className="text-secondary" />
                  <span className="source-doc-name">{src.document_name || src.document_id || 'Document'}</span>
                </div>
                <div className="source-chunk-meta">
                  <span className="source-meta-tag">
                    <Layers size={11} /> Chunk {src.chunk_index !== undefined ? src.chunk_index : idx}
                  </span>
                  {src.page_number !== null && src.page_number !== undefined && (
                    <span className="source-meta-tag">
                      <Hash size={11} /> Page {src.page_number}
                    </span>
                  )}
                  {src.score !== null && src.score !== undefined && (
                    <span className="source-meta-tag">
                      Score: {typeof src.score === 'number' ? src.score.toFixed(2) : src.score}
                    </span>
                  )}
                </div>
              </div>

              {src.text && (
                <div className="source-chunk-body">
                  <p className="source-chunk-text">"{src.text}"</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
