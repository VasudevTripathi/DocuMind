import React from 'react';
import { UploadDropzone } from './components/UploadDropzone';
import { AiCopilotPanel } from './components/AiCopilotPanel';
import { RecentDocuments } from './components/RecentDocuments';
import { QuickActions } from './components/QuickActions';
import { StatCard } from '../../components/ui/StatCard';
import { FileText, HardDrive, Zap, BookOpen } from 'lucide-react';
import './Dashboard.css';

export const Dashboard = () => {
  return (
    <div className="dashboard-container">
      {/* Top Hero Section */}
      <UploadDropzone />

      {/* Greeting */}
      <div className="dashboard-greeting">
        <h2>Good evening, Mr. Tripathi <span className="wave">👋</span></h2>
        <p className="text-secondary">Here's what's happening with your documents today.</p>
      </div>

      {/* Main Grid */}
      <div className="dashboard-grid">
        <div className="dashboard-main-col">
          {/* Stats Row */}
          <div className="stats-grid">
            <StatCard 
              title="Documents" 
              value="24" 
              change="12%" 
              icon={<FileText size={24} />} 
            />
            <StatCard 
              title="Total Words" 
              value="186K" 
              change="18%" 
              icon={<HardDrive size={24} />} 
            />
            <StatCard 
              title="Chunks" 
              value="82" 
              change="5%" 
              icon={<Zap size={24} />} 
            />
            <StatCard 
              title="Research Papers" 
              value="12" 
              change="33%" 
              icon={<BookOpen size={24} />} 
            />
          </div>

          <AiCopilotPanel />
          <RecentDocuments />
        </div>

        <div className="dashboard-side-col">
          <QuickActions />
        </div>
      </div>
    </div>
  );
};
