import React, { useState } from 'react';
import { AiCopilotPanel } from './components/AiCopilotPanel';
import { RecentDocuments } from './components/RecentDocuments';
import { QuickActions } from './components/QuickActions';
import { StatCard } from '../../components/ui/StatCard';
import { FileText, Zap, BookOpen, AlertCircle, Edit2, Check, X, User } from 'lucide-react';
import { useDocuments } from '../../hooks/useDocuments';
import { useUser } from '../../hooks/useUser';
import './Dashboard.css';

export const Dashboard = () => {
  const { documents, isLoading } = useDocuments();
  const { userName, setUserName, getGreeting } = useUser();
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(userName || '');

  const totalDocs = documents.length;
  const analyzedDocs = documents.filter(d => (d.status || '').toLowerCase() === 'analyzed').length;
  const processingDocs = documents.filter(d => ['processing', 'pending'].includes((d.status || '').toLowerCase())).length;
  const failedDocs = documents.filter(d => (d.status || '').toLowerCase() === 'failed').length;

  const greetingPrefix = getGreeting();

  const handleStartEdit = () => {
    setNameInput(userName || '');
    setIsEditingName(true);
  };

  const handleSaveName = (e) => {
    if (e) e.preventDefault();
    setUserName(nameInput.trim());
    setIsEditingName(false);
  };

  const handleCancelEdit = () => {
    setNameInput(userName || '');
    setIsEditingName(false);
  };

  return (
    <div className="dashboard-container">
      {/* Greeting */}
      <div className="dashboard-greeting">
        {isEditingName ? (
          <form className="name-edit-form" onSubmit={handleSaveName}>
            <span className="greeting-text">{greetingPrefix},</span>
            <input
              type="text"
              autoFocus
              className="name-edit-input"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              placeholder="Your name..."
              maxLength={40}
            />
            <button type="submit" className="name-edit-btn save" title="Save name">
              <Check size={16} />
            </button>
            <button type="button" className="name-edit-btn cancel" onClick={handleCancelEdit} title="Cancel">
              <X size={16} />
            </button>
          </form>
        ) : (
          <div className="greeting-header-row">
            <h2>
              {greetingPrefix}{userName ? `, ${userName}` : ''} <span className="wave">👋</span>
            </h2>
            <button
              type="button"
              className="edit-name-trigger-btn"
              onClick={handleStartEdit}
              title={userName ? "Change your name" : "Set your name"}
              aria-label="Edit name"
            >
              <Edit2 size={14} />
              <span>{userName ? "Edit" : "Set name"}</span>
            </button>
          </div>
        )}
        <p className="text-secondary">Here's what's happening with your documents today.</p>
      </div>

      {/* Main Grid */}
      <div className="dashboard-grid">
        <div className="dashboard-main-col">
          <AiCopilotPanel />
          
          {/* Stats Row */}
          <div className="stats-grid">
            <StatCard 
              title="Total Documents" 
              value={isLoading ? '...' : totalDocs.toString()} 
              icon={<FileText size={24} />} 
            />
            <StatCard 
              title="Analyzed" 
              value={isLoading ? '...' : analyzedDocs.toString()} 
              icon={<BookOpen size={24} />} 
            />
            <StatCard 
              title="Processing" 
              value={isLoading ? '...' : processingDocs.toString()} 
              icon={<Zap size={24} />} 
            />
            <StatCard 
              title="Failed" 
              value={isLoading ? '...' : failedDocs.toString()} 
              icon={<AlertCircle size={24} />} 
            />
          </div>

          <RecentDocuments />
        </div>

        <div className="dashboard-side-col">
          <QuickActions />
        </div>
      </div>
    </div>
  );
};
