import React from 'react';
import { GlassPanel } from '../../../components/ui/GlassPanel';
import { Bot, ArrowRight } from 'lucide-react';
import { Button } from '../../../components/ui/Button';

export const AiCopilotPanel = () => {
  return (
    <GlassPanel className="copilot-panel">
      <div className="copilot-header">
        <div className="copilot-icon-wrapper">
          <Bot size={24} className="text-accent-secondary" />
        </div>
        <div className="copilot-title-area">
          <h3>AI Assistant</h3>
          <p className="text-secondary text-sm">Get instant insights, summaries and answers from your documents.</p>
        </div>
      </div>
      
      <div className="dropzone-area">
        <div className="dropzone-icon">↑</div>
        <p className="dropzone-text">Drop your document here</p>
        <p className="dropzone-subtext text-tertiary">PDF, DOCX, TXT, PPT, Images (Max 50MB)</p>
        <Button variant="primary" className="mt-4">
          Upload Document <span>∨</span>
        </Button>
      </div>
    </GlassPanel>
  );
};
