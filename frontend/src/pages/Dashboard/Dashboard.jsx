import React from 'react';
import { AiCopilotPanel } from './components/AiCopilotPanel';
import { RecentDocuments } from './components/RecentDocuments';
import { QuickActions } from './components/QuickActions';
import { StatCard } from '../../components/ui/StatCard';
import { FileText, HardDrive, Zap, BookOpen } from 'lucide-react';
import { useDocuments } from '../../hooks/useDocuments';
import './Dashboard.css';

export const Dashboard = () => {
  const { documents, isLoading } = useDocuments();

  const totalDocs = documents.length;
  const analyzedDocs = documents.filter(d => (d.status || '').toLowerCase() === 'analyzed').length;
  const processingDocs = documents.filter(d => ['processing', 'pending'].includes((d.status || '').toLowerCase())).length;

  return (
    <div className="dashboard-container">
      {/* Greeting */}
      <div className="dashboard-greeting">
        <h2>Good evening, Mr. Tripathi <span className="wave">👋</span></h2>
        <p className="text-secondary">Here's what's happening with your documents today.</p>
      </div>

      {/* Main Grid */}
      <div className="dashboard-grid">
        <div className="dashboard-main-col">
          <AiCopilotPanel />
          
          {/* Stats Row */}
          <div className="stats-grid">
            <StatCard 
              title="Documents" 
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
              title="Total Words" 
              value="—" 
              change="Pending backend" 
              icon={<HardDrive size={24} />} 
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
