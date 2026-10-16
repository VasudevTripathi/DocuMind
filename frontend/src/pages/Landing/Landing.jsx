import React from 'react';
import { UploadDropzone } from '../Dashboard/components/UploadDropzone';
import { Zap, ArrowRight, User } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useUser } from '../../hooks/useUser';
import '../../components/layout/layout.css';
import './Landing.css';

export const Landing = ({ initialOpenNamePrompt = false }) => {
  const { userName } = useUser();

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
          {userName ? (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <User size={15} />
              <span>{userName}</span>
              <ArrowRight size={14} />
            </span>
          ) : (
            <span>Go to Dashboard</span>
          )}
        </Link>
      </header>
      <main className="landing-main">
        <UploadDropzone initialOpenNamePrompt={initialOpenNamePrompt} />
      </main>
    </div>
  );
};
