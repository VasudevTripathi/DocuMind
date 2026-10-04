import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  BarChart2, FileText, Database, Sparkles, Layers, 
  RefreshCw, MessageSquare, CheckSquare, TrendingUp, 
  Folder, HardDrive, AlertCircle, CheckCircle2, Clock
} from 'lucide-react';
import { GlassPanel } from '../../components/ui/GlassPanel';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { analyticsService } from '../../services/analyticsService';
import './Analytics.css';

export const Analytics = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchAnalytics = async () => {
    setIsRefreshing(true);
    setError(null);
    try {
      const res = await analyticsService.getAnalytics();
      setData(res);
    } catch (err) {
      setError(err.message || 'Failed to load library analytics.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const categoriesList = useMemo(() => {
    if (!data?.categories) return [];
    const total = data.total_documents || 1;
    return Object.entries(data.categories).map(([cat, count]) => ({
      name: cat,
      count,
      pct: Math.round((count / total) * 100)
    })).sort((a, b) => b.count - a.count);
  }, [data]);

  if (isLoading) {
    return (
      <div className="analytics-container">
        <GlassPanel className="analytics-state-wrapper">
          <div className="spinner" />
          <p>Analyzing library documents and vector index...</p>
        </GlassPanel>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics-container">
        <GlassPanel className="analytics-state-wrapper">
          <AlertCircle size={36} className="text-danger" />
          <h3>Unable to load analytics</h3>
          <p className="text-secondary">{error}</p>
          <Button variant="primary" onClick={fetchAnalytics}>
            <RefreshCw size={14} /> Retry
          </Button>
        </GlassPanel>
      </div>
    );
  }

  const {
    total_documents = 0,
    analyzed_count = 0,
    processing_count = 0,
    failed_count = 0,
    total_chunks = 0,
    total_words = 0,
    total_size_bytes = 0,
    vector_count = 0,
    file_types = {},
    top_entities = [],
    documents = []
  } = data || {};

  return (
    <div className="analytics-container">
      {/* Header */}
      <div className="analytics-header">
        <div className="analytics-header-left">
          <h1>Library Analytics</h1>
          <p className="text-secondary text-sm">
            Real-time intelligence, category breakdown, token density, and concept extraction.
          </p>
        </div>
        <div className="analytics-header-actions">
          <Button 
            variant="secondary" 
            onClick={fetchAnalytics}
            disabled={isRefreshing}
          >
            <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
          <Button variant="primary" onClick={() => navigate('/chat')}>
            <MessageSquare size={14} /> Open Copilot
          </Button>
        </div>
      </div>

      {/* Top Stat Cards */}
      <div className="analytics-stats-grid">
        <GlassPanel className="analytics-stat-card">
          <div className="stat-info">
            <span className="stat-label">Total Documents</span>
            <span className="stat-value">{total_documents}</span>
            <span className="stat-subtext">
              <span className="text-success font-semibold">{analyzed_count} Analyzed</span>
              {processing_count > 0 && ` • ${processing_count} In Progress`}
            </span>
          </div>
          <div className="stat-icon-wrapper stat-icon-purple">
            <FileText size={22} />
          </div>
        </GlassPanel>

        <GlassPanel className="analytics-stat-card">
          <div className="stat-info">
            <span className="stat-label">Vector Embeddings</span>
            <span className="stat-value">{vector_count}</span>
            <span className="stat-subtext">
              Across {total_chunks} chunks (all-MiniLM-L6-v2)
            </span>
          </div>
          <div className="stat-icon-wrapper stat-icon-blue">
            <Database size={22} />
          </div>
        </GlassPanel>

        <GlassPanel className="analytics-stat-card">
          <div className="stat-info">
            <span className="stat-label">Total Words Indexed</span>
            <span className="stat-value">{total_words.toLocaleString()}</span>
            <span className="stat-subtext">
              Storage: {formatBytes(total_size_bytes)}
            </span>
          </div>
          <div className="stat-icon-wrapper stat-icon-green">
            <Layers size={22} />
          </div>
        </GlassPanel>

        <GlassPanel className="analytics-stat-card">
          <div className="stat-info">
            <span className="stat-label">Identified Entities</span>
            <span className="stat-value">{top_entities.length}</span>
            <span className="stat-subtext">
              Key topics & organizations detected
            </span>
          </div>
          <div className="stat-icon-wrapper stat-icon-orange">
            <Sparkles size={22} />
          </div>
        </GlassPanel>
      </div>

      {/* Two Column Section */}
      <div className="analytics-grid-two">
        {/* Category Breakdown */}
        <GlassPanel className="analytics-panel">
          <div className="panel-header">
            <span className="panel-title">
              <Folder size={18} className="text-accent-primary" /> Category Distribution
            </span>
            <span className="text-secondary text-xs">{categoriesList.length} Categories</span>
          </div>

          {categoriesList.length === 0 ? (
            <p className="text-secondary text-sm">No categories detected yet.</p>
          ) : (
            <div className="category-list">
              {categoriesList.map((cat) => (
                <div key={cat.name} className="category-item">
                  <div className="category-item-meta">
                    <span className="category-name">{cat.name}</span>
                    <span className="category-count">{cat.count} docs ({cat.pct}%)</span>
                  </div>
                  <div className="category-bar-bg">
                    <div 
                      className="category-bar-fill" 
                      style={{ width: `${Math.max(cat.pct, 4)}%` }} 
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassPanel>

        {/* File Formats & Processing Health */}
        <GlassPanel className="analytics-panel">
          <div className="panel-header">
            <span className="panel-title">
              <HardDrive size={18} className="text-accent-secondary" /> Formats & Processing Pipeline
            </span>
          </div>

          <div className="distribution-row">
            <div className="dist-chip">
              <span className="dist-chip-label">PDF Documents</span>
              <span className="dist-chip-val">{file_types['PDF'] || 0}</span>
            </div>
            <div className="dist-chip">
              <span className="dist-chip-label">Word DOCX</span>
              <span className="dist-chip-val">{file_types['DOCX'] || 0}</span>
            </div>
            <div className="dist-chip">
              <span className="dist-chip-label">Plain TXT</span>
              <span className="dist-chip-val">{file_types['TXT'] || 0}</span>
            </div>
          </div>

          <div style={{ marginTop: 'var(--space-2)' }}>
            <span className="text-secondary text-xs font-semibold uppercase tracking-wider block mb-2">
              Ingestion Status Health
            </span>
            <div className="distribution-row">
              <div className="dist-chip" style={{ borderColor: 'rgba(52, 211, 153, 0.3)' }}>
                <span className="dist-chip-label text-success">Analyzed / Ready</span>
                <span className="dist-chip-val">{analyzed_count}</span>
              </div>
              <div className="dist-chip" style={{ borderColor: 'rgba(96, 165, 250, 0.3)' }}>
                <span className="dist-chip-label text-accent-primary">Processing</span>
                <span className="dist-chip-val">{processing_count}</span>
              </div>
              <div className="dist-chip" style={{ borderColor: failed_count > 0 ? 'rgba(239, 68, 68, 0.3)' : 'rgba(255, 255, 255, 0.08)' }}>
                <span className="dist-chip-label text-danger">Failed</span>
                <span className="dist-chip-val">{failed_count}</span>
              </div>
            </div>
          </div>
        </GlassPanel>
      </div>

      {/* Extracted Entities Concept Cloud */}
      {top_entities.length > 0 && (
        <GlassPanel className="analytics-panel">
          <div className="panel-header">
            <span className="panel-title">
              <Sparkles size={18} className="text-warning" /> Extracted Concepts & Key Entities
            </span>
            <span className="text-secondary text-xs">Identified across document texts</span>
          </div>
          <div className="entities-cloud">
            {top_entities.map((ent, idx) => (
              <span key={`${ent.name}-${idx}`} className="entity-pill">
                <span>{ent.name}</span>
                <span className="entity-pill-badge">{ent.count}</span>
              </span>
            ))}
          </div>
        </GlassPanel>
      )}

      {/* Document Intelligence Roster */}
      <GlassPanel className="analytics-panel">
        <div className="panel-header">
          <span className="panel-title">
            <BarChart2 size={18} className="text-accent-primary" /> Document Intelligence Roster
          </span>
          <span className="text-secondary text-xs">{documents.length} items</span>
        </div>

        <div className="intelligence-table-wrapper">
          <table className="intelligence-table">
            <thead>
              <tr>
                <th>Document Name</th>
                <th>Category</th>
                <th>Format</th>
                <th>Chunks</th>
                <th>Words</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>
                    <div className="doc-name-cell">
                      <FileText size={15} className="text-accent-primary" />
                      <span>{doc.name}</span>
                    </div>
                  </td>
                  <td>
                    <Badge variant="default">{doc.category}</Badge>
                  </td>
                  <td>{doc.file_type}</td>
                  <td>{doc.chunk_count}</td>
                  <td>{doc.word_count.toLocaleString()}</td>
                  <td>
                    <Badge variant={doc.status === 'analyzed' ? 'success' : doc.status === 'failed' ? 'danger' : 'warning'}>
                      {doc.status}
                    </Badge>
                  </td>
                  <td>
                    <div className="actions-cell">
                      <Button 
                        variant="secondary" 
                        size="sm"
                        onClick={() => navigate('/chat')}
                        title="Chat about this document"
                      >
                        <MessageSquare size={13} />
                      </Button>
                      <Button 
                        variant="secondary" 
                        size="sm"
                        onClick={() => navigate('/compare')}
                        title="Compare with another document"
                      >
                        <CheckSquare size={13} />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassPanel>
    </div>
  );
};
