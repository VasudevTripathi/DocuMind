import React from 'react';
import { UploadDropzone } from '../Dashboard/components/UploadDropzone';
import { Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import '../../components/layout/layout.css';
import './Landing.css';

export const Landing = () => {
  return (
    <div className="landing-container">
      <header className="landing-header">
        <Link to="/" className="brand">
          <div className="brand-logo">
            <Zap size={20} className="text-accent-primary" />
          </div>
          <span className="brand-name">DocuMind AI</span>
        </Link>
        <Link to="/dashboard" className="landing-dashboard-btn">
          Go to Dashboard
        </Link>
      </header>
      <main className="landing-main">
        <UploadDropzone />
      </main>
    </div>
  );
};
