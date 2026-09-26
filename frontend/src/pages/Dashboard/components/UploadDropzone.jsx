import React, { useState } from 'react';
import { Upload, FileText, Image as ImageIcon, Link as LinkIcon, ArrowRight, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { GlassPanel } from '../../../components/ui/GlassPanel';
import { Button } from '../../../components/ui/Button';
import '../../Landing/Landing.css';

export const UploadDropzone = () => {
  const navigate = useNavigate();
  const [showDemoModal, setShowDemoModal] = useState(false);

  return (
    <div className="upload-hero">
      <div className="upload-content">
        <div className="ai-badge">
          <span className="sparkle">✨</span> AI-Powered Document Intelligence
        </div>
        <h1 className="hero-title">
          Turn complex documents into <br/>
          <span className="gradient-text">clear insights.</span>
        </h1>
        <p className="hero-subtitle text-secondary">
          Upload, analyze, search, and chat with your documents. Research papers, reports, contracts — everything in one intelligent workspace.
        </p>
        <div className="hero-actions">
          <Button variant="primary" className="btn-lg" onClick={() => navigate('/dashboard')}>
            Get Started <ArrowRight size={16} />
          </Button>
          <Button variant="secondary" className="btn-lg" onClick={() => setShowDemoModal(true)}>
            <span className="play-icon">▶</span> Watch Demo
          </Button>
        </div>
        <div className="supported-formats text-tertiary">
          <div className="format-item"><FileText size={16} className="text-danger" /> PDF</div>
          <div className="format-item"><FileText size={16} className="text-accent-secondary" /> DOCX</div>
          <div className="format-item"><FileText size={16} /> TXT</div>
          <div className="format-item"><ImageIcon size={16} className="text-success" /> Images</div>
          <div className="format-item"><LinkIcon size={16} /> Web Links</div>
          <span>and more</span>
        </div>
      </div>

      <div className="upload-visual-area">
        <GlassPanel className="ai-menu-panel">
          <div className="ai-menu-item"><span className="menu-icon bg-purple">📝</span> AI Summary</div>
          <div className="ai-menu-item"><span className="menu-icon bg-orange">💡</span> Key Findings</div>
          <div className="ai-menu-item"><span className="menu-icon bg-green">🧩</span> Entities</div>
          <div className="ai-menu-item"><span className="menu-icon bg-blue">💬</span> Ask Questions</div>
          <div className="ai-menu-item"><span className="menu-icon bg-red">⚖️</span> Compare</div>
        </GlassPanel>
        
        <div className="document-graphic-mock">
          <div className="doc-page">
            <div className="doc-mock-title"></div>
            <div className="doc-mock-line full"></div>
            <div className="doc-mock-line almost-full"></div>
            <div className="doc-mock-line partial"></div>
            <div className="doc-mock-entities">
              <span className="doc-entity purple"></span>
              <span className="doc-entity blue"></span>
            </div>
            <div className="doc-mock-line full"></div>
            <div className="doc-mock-line medium"></div>
            
            <div className="doc-highlight-area"></div>
          </div>
          
          <motion.div className="floating-insight pos-1" animate={{ y: [-5, 5, -5] }} transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}>
            ✨ AI Summary
          </motion.div>
          <motion.div className="floating-insight pos-2" animate={{ y: [5, -5, 5] }} transition={{ repeat: Infinity, duration: 5, ease: "easeInOut", delay: 1 }}>
            💡 Key Findings
          </motion.div>
          <motion.div className="floating-insight pos-3" animate={{ y: [-3, 3, -3] }} transition={{ repeat: Infinity, duration: 4.5, ease: "easeInOut", delay: 2 }}>
            🧩 Entities
          </motion.div>
          <motion.div className="floating-insight pos-4" animate={{ y: [4, -4, 4] }} transition={{ repeat: Infinity, duration: 5.5, ease: "easeInOut", delay: 1.5 }}>
            💬 Ask Questions
          </motion.div>
          <motion.div className="floating-insight pos-5" animate={{ y: [-4, 4, -4] }} transition={{ repeat: Infinity, duration: 6, ease: "easeInOut", delay: 0.5 }}>
            ⚖️ Compare
          </motion.div>
        </div>
      </div>

      {showDemoModal && (
        <div 
          className="demo-modal-overlay"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: 'var(--space-4)'
          }}
          onClick={() => setShowDemoModal(false)}
        >
          <div 
            className="demo-modal-content"
            style={{
              background: 'var(--bg-surface)',
              border: 'var(--border-glass)',
              borderRadius: 'var(--radius-lg)',
              padding: 'var(--space-6)',
              maxWidth: '440px',
              width: '100%',
              boxShadow: 'var(--shadow-glow)',
              position: 'relative'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
              <h3 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--text-primary)' }}>
                DocuMind AI Demo
              </h3>
              <button
                onClick={() => setShowDemoModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  borderRadius: 'var(--radius-sm)'
                }}
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', lineHeight: 1.6, marginBottom: 'var(--space-6)' }}>
              Upload a document, analyze it with AI, search its contents, and chat with your document.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-3)' }}>
              <Button variant="secondary" onClick={() => setShowDemoModal(false)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
