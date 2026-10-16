import React, { useState, useEffect } from 'react';
import { Upload, FileText, Image as ImageIcon, Link as LinkIcon, ArrowRight, X, User, Sparkles, Check } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { GlassPanel } from '../../../components/ui/GlassPanel';
import { Button } from '../../../components/ui/Button';
import { useUser } from '../../../hooks/useUser';
import '../../Landing/Landing.css';

export const UploadDropzone = ({ initialOpenNamePrompt = false }) => {
  const navigate = useNavigate();
  const { userName, setUserName } = useUser();
  const [showDemoModal, setShowDemoModal] = useState(false);
  const [showNameModal, setShowNameModal] = useState(Boolean(initialOpenNamePrompt));
  const [nameInput, setNameInput] = useState(userName || '');
  const [modalNameInput, setModalNameInput] = useState(userName || '');

  useEffect(() => {
    if (userName) {
      setNameInput(userName);
      setModalNameInput(userName);
    }
  }, [userName]);

  useEffect(() => {
    if (initialOpenNamePrompt) {
      setShowNameModal(true);
    }
  }, [initialOpenNamePrompt]);

  const handleGetStartedForm = (e) => {
    if (e) e.preventDefault();
    const trimmed = nameInput.trim();
    if (trimmed) {
      setUserName(trimmed);
      navigate('/dashboard');
    } else if (userName) {
      navigate('/dashboard');
    } else {
      setShowNameModal(true);
    }
  };

  const handleModalSubmit = (e) => {
    if (e) e.preventDefault();
    const trimmed = modalNameInput.trim();
    if (trimmed) {
      setUserName(trimmed);
    }
    setShowNameModal(false);
    navigate('/dashboard');
  };

  const handleSkipModal = () => {
    setShowNameModal(false);
    navigate('/dashboard');
  };

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

        {/* Get Started / User Name Action Section */}
        <div className="hero-get-started-section">
          <form className="hero-name-form" onSubmit={handleGetStartedForm}>
            <div className="hero-name-input-wrapper">
              <User size={18} className="hero-name-icon" />
              <input
                type="text"
                placeholder={userName ? `Welcome back, ${userName}` : "Enter your name to get started..."}
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                className="hero-name-input"
                aria-label="User name input"
                maxLength={40}
              />
              {nameInput.trim() && (
                <button
                  type="button"
                  className="hero-name-clear-btn"
                  onClick={() => setNameInput('')}
                  aria-label="Clear name"
                >
                  <X size={14} />
                </button>
              )}
            </div>
            <div className="hero-actions-row">
              <Button type="submit" variant="primary" className="btn-lg get-started-submit-btn">
                {nameInput.trim() || userName ? 'Get Started' : 'Get Started'} <ArrowRight size={16} />
              </Button>
              <Button type="button" variant="secondary" className="btn-lg" onClick={() => setShowDemoModal(true)}>
                <span className="play-icon">▶</span> Watch Demo
              </Button>
            </div>
          </form>

          {userName && (
            <div className="user-greeting-pill">
              <span className="pill-dot"></span>
              <span>Currently set for: <strong>{userName}</strong></span>
              <button 
                type="button" 
                className="pill-change-btn" 
                onClick={() => { setUserName(''); setNameInput(''); setModalNameInput(''); }}
              >
                (Switch)
              </button>
            </div>
          )}
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

      {/* Name Input Modal */}
      {showNameModal && (
        <div 
          className="demo-modal-overlay name-prompt-overlay"
          onClick={() => setShowNameModal(false)}
        >
          <div 
            className="demo-modal-content name-prompt-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="name-prompt-header">
              <div className="name-prompt-icon-box">
                <Sparkles size={24} className="text-accent-primary" />
              </div>
              <button
                onClick={() => setShowNameModal(false)}
                className="name-prompt-close"
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <h3 className="name-prompt-title">
              Welcome to DocuMind AI 👋
            </h3>
            <p className="name-prompt-subtitle">
              What should we call you? We'll personalize your workspace and document dashboard.
            </p>

            <form onSubmit={handleModalSubmit} className="name-prompt-form">
              <div className="hero-name-input-wrapper modal-input-wrapper">
                <User size={18} className="hero-name-icon" />
                <input
                  type="text"
                  autoFocus
                  placeholder="Enter your name (e.g., Alex, Vasu)..."
                  value={modalNameInput}
                  onChange={(e) => setModalNameInput(e.target.value)}
                  className="hero-name-input"
                  maxLength={40}
                />
              </div>

              <div className="name-prompt-actions">
                <Button 
                  type="button" 
                  variant="secondary" 
                  onClick={handleSkipModal}
                  className="skip-btn"
                >
                  Continue as Guest
                </Button>
                <Button 
                  type="submit" 
                  variant="primary"
                  className="continue-btn"
                >
                  Continue to Dashboard <ArrowRight size={16} />
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Demo Modal */}
      {showDemoModal && (
        <div 
          className="demo-modal-overlay"
          onClick={() => setShowDemoModal(false)}
        >
          <div 
            className="demo-modal-content"
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
              Upload a document, analyze it with AI, search its contents, and chat with your document in an interactive, grounded environment.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-3)' }}>
              <Button variant="secondary" onClick={() => setShowDemoModal(false)}>
                Close
              </Button>
              <Button variant="primary" onClick={() => { setShowDemoModal(false); setShowNameModal(true); }}>
                Get Started <ArrowRight size={16} />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
