import React from 'react';
import { UploadDropzone } from '../Dashboard/components/UploadDropzone';
import { GlassPanel } from '../../components/ui/GlassPanel';
import { Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import '../../components/layout/layout.css';
import '../Dashboard/Dashboard.css';

export const Landing = () => {
  return (
    <div className="landing-container" style={{ minHeight: '100vh', background: 'var(--bg-base)', padding: 'var(--space-6)' }}>
      <header className="landing-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-8)' }}>
        <Link to="/" className="brand" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', textDecoration: 'none', color: 'inherit' }}>
          <div className="brand-logo" style={{ width: '32px', height: '32px', borderRadius: 'var(--radius-md)', background: 'rgba(123, 63, 228, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Zap size={20} className="text-accent-primary" />
          </div>
          <span className="brand-name" style={{ fontWeight: '600', fontSize: 'var(--font-size-lg)', color: 'var(--text-primary)' }}>DocuMind AI</span>
        </Link>
        <Link to="/dashboard" style={{ padding: 'var(--space-2) var(--space-4)', background: 'rgba(255,255,255,0.05)', borderRadius: 'var(--radius-md)', color: 'var(--text-primary)', textDecoration: 'none', border: 'var(--border-glass)' }}>
          Go to Dashboard
        </Link>
      </header>
      <main>
        <UploadDropzone />
      </main>
    </div>
  );
};
