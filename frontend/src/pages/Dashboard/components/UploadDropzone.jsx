import React from 'react';
import { Upload, FileText, Image as ImageIcon, Link as LinkIcon, ArrowRight } from 'lucide-react';
import { GlassPanel } from '../../../components/ui/GlassPanel';
import { Button } from '../../../components/ui/Button';
import '../Dashboard.css';

export const UploadDropzone = () => {
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
          <Button variant="primary" className="btn-lg">
            Get Started <ArrowRight size={16} />
          </Button>
          <Button variant="secondary" className="btn-lg">
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
        
        {/* Placeholder for the document graphic in the reference */}
        <div className="document-graphic-mock">
          <div className="doc-page">
            <div className="doc-line w-3/4"></div>
            <div className="doc-line w-full"></div>
            <div className="doc-line w-5/6"></div>
            <div className="processing-chip">
              <div className="spinner"></div> Summarizing...
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
