import React, { useState, useMemo } from 'react';
import { 
  GitCompare, ArrowLeftRight, CheckCircle2, AlertTriangle, 
  ShieldAlert, PlusCircle, MinusCircle, RefreshCw, FileText, 
  Sparkles, Layers, Search, ArrowRight, X, AlertCircle, Info,
  Loader2, Filter, ChevronDown, Check, Zap
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../../components/ui/GlassPanel';
import { ClayPanel } from '../../components/ui/ClayPanel';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { useDocuments } from '../../hooks/useDocuments';
import { comparisonService } from '../../services/comparisonService';
import { SourceEvidence } from '../../components/Compare/SourceEvidence';
import { GroundingPanel } from '../../components/Compare/GroundingPanel';
import './Compare.css';

export const Compare = () => {
  const { documents, isLoading: isLoadingDocs, error: docsError } = useDocuments();

  // Document Selection State
  const [docAId, setDocAId] = useState('');
  const [docBId, setDocBId] = useState('');
  const [focusQuery, setFocusQuery] = useState('');

  // Execution & Results State
  const [isComparing, setIsComparing] = useState(false);
  const [comparisonResult, setComparisonResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [activeTab, setActiveTab] = useState('all'); // 'all', 'conflicts', 'modifications', 'additions', 'removals', 'common'

  // Dropdown search filters
  const [searchA, setSearchA] = useState('');
  const [searchB, setSearchB] = useState('');
  const [isDropdownAOpen, setIsDropdownAOpen] = useState(false);
  const [isDropdownBOpen, setIsDropdownBOpen] = useState(false);

  // Selected document objects
  const docA = useMemo(() => documents.find(d => d.id === docAId) || null, [documents, docAId]);
  const docB = useMemo(() => documents.find(d => d.id === docBId) || null, [documents, docBId]);

  // Filtered document options for dropdowns
  const availableDocsA = useMemo(() => {
    if (!searchA.trim()) return documents;
    const q = searchA.toLowerCase().trim();
    return documents.filter(d => d.name.toLowerCase().includes(q) || d.category?.toLowerCase().includes(q));
  }, [documents, searchA]);

  const availableDocsB = useMemo(() => {
    if (!searchB.trim()) return documents;
    const q = searchB.toLowerCase().trim();
    return documents.filter(d => d.name.toLowerCase().includes(q) || d.category?.toLowerCase().includes(q));
  }, [documents, searchB]);

  // Validation
  const isSameDoc = Boolean(docAId && docBId && docAId === docBId);
  const canCompare = Boolean(docAId && docBId && !isSameDoc && !isComparing);

  // Swap Documents A <-> B
  const handleSwap = () => {
    if (isComparing) return;
    const tempId = docAId;
    setDocAId(docBId);
    setDocBId(tempId);
    // If we have existing results, swap document perspectives or re-run
    setComparisonResult(null);
  };

  // Run Comparison
  const handleRunComparison = async (e) => {
    e?.preventDefault();
    if (!canCompare) return;

    setIsComparing(true);
    setErrorMessage(null);

    try {
      const result = await comparisonService.compareDocuments(docAId, docBId, focusQuery);
      setComparisonResult(result);
      setActiveTab('all');
    } catch (err) {
      console.error('Document comparison error:', err);
      setErrorMessage(err.message || 'Failed to compare documents.');
      setComparisonResult(null);
    } finally {
      setIsComparing(false);
    }
  };

  // Counts from backend result
  const additions = comparisonResult?.additions || [];
  const removals = comparisonResult?.removals || [];
  const modifications = comparisonResult?.modifications || [];
  const conflicts = comparisonResult?.conflicts || [];
  const common = comparisonResult?.common || [];
  const totalDifferences = additions.length + removals.length + modifications.length + conflicts.length;

  return (
    <div className="compare-page-container">
      {/* Page Header */}
      <header className="compare-header">
        <div className="compare-header-content">
          <div className="compare-header-title-row">
            <div className="compare-header-icon-wrapper">
              <GitCompare size={24} className="text-accent-primary" />
            </div>
            <div>
              <h1 className="compare-title">Compare Documents</h1>
              <p className="compare-subtitle">
                Side-by-side evidence analysis to identify additions, removals, changed specifications, and conflicting statements.
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Setup / Document Selector Panel */}
      <GlassPanel className="compare-setup-panel">
        <form onSubmit={handleRunComparison} className="compare-form">
          <div className="selectors-grid">
            {/* Document A Selector */}
            <div className="selector-column">
              <div className="selector-label-group">
                <span className="selector-badge badge-doc-a">Document A</span>
                <span className="selector-role">Baseline Reference</span>
              </div>

              <div className="doc-select-container">
                <div 
                  className={`doc-select-trigger ${isDropdownAOpen ? 'is-open' : ''} ${!docA ? 'is-empty' : ''}`}
                  onClick={() => !isComparing && setIsDropdownAOpen(!isDropdownAOpen)}
                >
                  {docA ? (
                    <div className="selected-doc-display">
                      <FileText size={18} className="text-secondary shrink-0" />
                      <div className="selected-doc-details">
                        <span className="selected-doc-name" title={docA.name}>{docA.name}</span>
                        <div className="selected-doc-subtags">
                          <span className="doc-subtag">{docA.type?.toUpperCase() || 'FILE'}</span>
                          <span className="doc-subtag">{docA.category || 'General'}</span>
                          {docA.size && <span className="doc-subtag">{docA.size}</span>}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <span className="select-placeholder">Select baseline document...</span>
                  )}
                  <ChevronDown size={16} className="trigger-arrow" />
                </div>

                {isDropdownAOpen && (
                  <div className="doc-dropdown-menu">
                    <div className="dropdown-search-box">
                      <Search size={14} className="dropdown-search-icon" />
                      <input 
                        type="text"
                        placeholder="Filter documents..."
                        value={searchA}
                        onChange={(e) => setSearchA(e.target.value)}
                        className="dropdown-search-input"
                        autoFocus
                      />
                    </div>
                    <div className="dropdown-list">
                      {availableDocsA.length > 0 ? (
                        availableDocsA.map((d) => (
                          <div 
                            key={d.id}
                            className={`dropdown-item ${d.id === docAId ? 'is-selected' : ''}`}
                            onClick={() => {
                              setDocAId(d.id);
                              setIsDropdownAOpen(false);
                            }}
                          >
                            <FileText size={15} className="dropdown-item-icon" />
                            <div className="dropdown-item-info">
                              <span className="dropdown-item-name">{d.name}</span>
                              <span className="dropdown-item-category">{d.category || 'General'} • {d.size || '0 B'}</span>
                            </div>
                            {d.id === docAId && <Check size={14} className="dropdown-item-check" />}
                          </div>
                        ))
                      ) : (
                        <div className="dropdown-empty-item">No documents match search</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Swap Button */}
            <div className="swap-button-column">
              <button 
                type="button" 
                className="swap-btn"
                title="Swap Document A and Document B"
                onClick={handleSwap}
                disabled={isComparing || (!docAId && !docBId)}
              >
                <ArrowLeftRight size={18} />
              </button>
            </div>

            {/* Document B Selector */}
            <div className="selector-column">
              <div className="selector-label-group">
                <span className="selector-badge badge-doc-b">Document B</span>
                <span className="selector-role">Comparison Target</span>
              </div>

              <div className="doc-select-container">
                <div 
                  className={`doc-select-trigger ${isDropdownBOpen ? 'is-open' : ''} ${!docB ? 'is-empty' : ''}`}
                  onClick={() => !isComparing && setIsDropdownBOpen(!isDropdownBOpen)}
                >
                  {docB ? (
                    <div className="selected-doc-display">
                      <FileText size={18} className="text-secondary shrink-0" />
                      <div className="selected-doc-details">
                        <span className="selected-doc-name" title={docB.name}>{docB.name}</span>
                        <div className="selected-doc-subtags">
                          <span className="doc-subtag">{docB.type?.toUpperCase() || 'FILE'}</span>
                          <span className="doc-subtag">{docB.category || 'General'}</span>
                          {docB.size && <span className="doc-subtag">{docB.size}</span>}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <span className="select-placeholder">Select target document...</span>
                  )}
                  <ChevronDown size={16} className="trigger-arrow" />
                </div>

                {isDropdownBOpen && (
                  <div className="doc-dropdown-menu">
                    <div className="dropdown-search-box">
                      <Search size={14} className="dropdown-search-icon" />
                      <input 
                        type="text"
                        placeholder="Filter documents..."
                        value={searchB}
                        onChange={(e) => setSearchB(e.target.value)}
                        className="dropdown-search-input"
                        autoFocus
                      />
                    </div>
                    <div className="dropdown-list">
                      {availableDocsB.length > 0 ? (
                        availableDocsB.map((d) => (
                          <div 
                            key={d.id}
                            className={`dropdown-item ${d.id === docBId ? 'is-selected' : ''}`}
                            onClick={() => {
                              setDocBId(d.id);
                              setIsDropdownBOpen(false);
                            }}
                          >
                            <FileText size={15} className="dropdown-item-icon" />
                            <div className="dropdown-item-info">
                              <span className="dropdown-item-name">{d.name}</span>
                              <span className="dropdown-item-category">{d.category || 'General'} • {d.size || '0 B'}</span>
                            </div>
                            {d.id === docBId && <Check size={14} className="dropdown-item-check" />}
                          </div>
                        ))
                      ) : (
                        <div className="dropdown-empty-item">No documents match search</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Validation Warnings */}
          {isSameDoc && (
            <div className="compare-validation-message">
              <AlertTriangle size={15} className="text-warning shrink-0" />
              <span>Document A and Document B cannot be the same document. Select two distinct documents.</span>
            </div>
          )}

          {/* Optional Focus Input & Action Row */}
          <div className="compare-action-row">
            <div className="focus-input-wrapper">
              <span className="focus-input-label">Focus Area (Optional):</span>
              <div className="focus-input-box">
                <Search size={14} className="focus-icon text-tertiary" />
                <input 
                  type="text"
                  placeholder="e.g. pricing, security policy, deadlines, storage limits..."
                  value={focusQuery}
                  onChange={(e) => setFocusQuery(e.target.value)}
                  disabled={isComparing}
                  className="focus-input"
                />
                {focusQuery && (
                  <button 
                    type="button" 
                    className="focus-clear-btn" 
                    onClick={() => setFocusQuery('')}
                    disabled={isComparing}
                  >
                    <X size={13} />
                  </button>
                )}
              </div>
            </div>

            <Button 
              type="submit" 
              variant="primary" 
              className="compare-execute-btn"
              disabled={!canCompare}
            >
              {isComparing ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Aligning & Comparing...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Compare Documents</span>
                </>
              )}
            </Button>
          </div>
        </form>
      </GlassPanel>

      {/* Error Banner */}
      {errorMessage && (
        <div className="compare-error-banner">
          <AlertCircle size={18} className="text-danger shrink-0" />
          <div className="error-banner-content">
            <span className="error-banner-title">Comparison Error</span>
            <p className="error-banner-desc">{errorMessage}</p>
          </div>
          <button 
            type="button" 
            className="error-dismiss-btn"
            onClick={() => setErrorMessage(null)}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Loading Skeleton Indicator */}
      {isComparing && (
        <GlassPanel className="compare-loading-panel">
          <div className="loading-spinner-wrapper">
            <Loader2 size={36} className="animate-spin text-accent-primary" />
          </div>
          <h3 className="loading-title">Analyzing & Aligning Evidence</h3>
          <p className="loading-desc">
            Extracting statements, aligning cross-document vectors, detecting metric discrepancies, and verifying deterministic grounding...
          </p>
          <div className="loading-steps">
            <div className="loading-step active">
              <CheckCircle2 size={14} className="text-success" />
              <span>Evidence Chunk Extraction</span>
            </div>
            <div className="loading-step active">
              <CheckCircle2 size={14} className="text-success" />
              <span>Semantic Vector Alignment</span>
            </div>
            <div className="loading-step active">
              <Loader2 size={14} className="animate-spin text-accent-primary" />
              <span>Deterministic Difference Detection</span>
            </div>
          </div>
        </GlassPanel>
      )}

      {/* Comparison Results */}
      {!isComparing && comparisonResult && (
        <div className="compare-results-container">
          {/* Result Header & Document Comparison Meta */}
          <GlassPanel className="result-meta-card">
            <div className="result-meta-top">
              <div className="doc-meta-box doc-a-meta">
                <span className="meta-badge doc-a">Document A</span>
                <h3 className="meta-doc-name">{comparisonResult.document_a?.name}</h3>
                <div className="meta-doc-tags">
                  <span className="meta-doc-tag">{comparisonResult.document_a?.category || 'General'}</span>
                  <span className="meta-doc-tag">
                    <Layers size={11} /> {comparisonResult.document_a?.chunk_count || 0} Chunks
                  </span>
                </div>
              </div>

              <div className="versus-pill">
                <span>VS</span>
              </div>

              <div className="doc-meta-box doc-b-meta">
                <span className="meta-badge doc-b">Document B</span>
                <h3 className="meta-doc-name">{comparisonResult.document_b?.name}</h3>
                <div className="meta-doc-tags">
                  <span className="meta-doc-tag">{comparisonResult.document_b?.category || 'General'}</span>
                  <span className="meta-doc-tag">
                    <Layers size={11} /> {comparisonResult.document_b?.chunk_count || 0} Chunks
                  </span>
                </div>
              </div>
            </div>

            {/* Executive Summary */}
            <div className="result-summary-box">
              <div className="summary-header">
                <div className="summary-header-left">
                  <Sparkles size={16} className="text-accent-primary" />
                  <span className="summary-title">Executive Comparison Summary</span>
                </div>
                <div className="summary-header-right">
                  <span className="provider-tag">
                    {comparisonResult.provider === 'gemini' ? (
                      <>
                        <Zap size={12} className="text-accent-secondary" /> Gemini 2.5 Flash
                      </>
                    ) : (
                      'Deterministic Heuristic'
                    )}
                  </span>
                </div>
              </div>
              <p className="summary-content">{comparisonResult.summary}</p>
            </div>
          </GlassPanel>

          {/* Statistics Overview Cards */}
          <div className="statistics-grid">
            <div 
              className={`stat-card-pill ${activeTab === 'conflicts' ? 'is-active' : ''} stat-conflicts`}
              onClick={() => setActiveTab(activeTab === 'conflicts' ? 'all' : 'conflicts')}
            >
              <div className="stat-card-pill-top">
                <span className="stat-pill-label">Conflicts</span>
                <ShieldAlert size={16} className="stat-pill-icon text-danger" />
              </div>
              <span className="stat-pill-number text-danger">{conflicts.length}</span>
              <span className="stat-pill-hint">Opposing claims</span>
            </div>

            <div 
              className={`stat-card-pill ${activeTab === 'modifications' ? 'is-active' : ''} stat-modifications`}
              onClick={() => setActiveTab(activeTab === 'modifications' ? 'all' : 'modifications')}
            >
              <div className="stat-card-pill-top">
                <span className="stat-pill-label">Modifications</span>
                <AlertTriangle size={16} className="stat-pill-icon text-warning" />
              </div>
              <span className="stat-pill-number text-warning">{modifications.length}</span>
              <span className="stat-pill-hint">Updated details</span>
            </div>

            <div 
              className={`stat-card-pill ${activeTab === 'additions' ? 'is-active' : ''} stat-additions`}
              onClick={() => setActiveTab(activeTab === 'additions' ? 'all' : 'additions')}
            >
              <div className="stat-card-pill-top">
                <span className="stat-pill-label">Additions</span>
                <PlusCircle size={16} className="stat-pill-icon text-success" />
              </div>
              <span className="stat-pill-number text-success">{additions.length}</span>
              <span className="stat-pill-hint">New in Doc B</span>
            </div>

            <div 
              className={`stat-card-pill ${activeTab === 'removals' ? 'is-active' : ''} stat-removals`}
              onClick={() => setActiveTab(activeTab === 'removals' ? 'all' : 'removals')}
            >
              <div className="stat-card-pill-top">
                <span className="stat-pill-label">Removals</span>
                <MinusCircle size={16} className="stat-pill-icon text-danger" />
              </div>
              <span className="stat-pill-number text-danger">{removals.length}</span>
              <span className="stat-pill-hint">Omitted from Doc B</span>
            </div>

            <div 
              className={`stat-card-pill ${activeTab === 'common' ? 'is-active' : ''} stat-common`}
              onClick={() => setActiveTab(activeTab === 'common' ? 'all' : 'common')}
            >
              <div className="stat-card-pill-top">
                <span className="stat-pill-label">Common</span>
                <CheckCircle2 size={16} className="stat-pill-icon text-secondary" />
              </div>
              <span className="stat-pill-number text-secondary">{common.length}</span>
              <span className="stat-pill-hint">Identical points</span>
            </div>
          </div>

          {/* Category Filter Tabs */}
          <div className="diff-tabs-wrapper">
            <button 
              type="button"
              className={`diff-tab-btn ${activeTab === 'all' ? 'active' : ''}`}
              onClick={() => setActiveTab('all')}
            >
              All Differences <span className="tab-count">{totalDifferences}</span>
            </button>
            <button 
              type="button"
              className={`diff-tab-btn tab-conflict ${activeTab === 'conflicts' ? 'active' : ''}`}
              onClick={() => setActiveTab('conflicts')}
            >
              Conflicts <span className="tab-count">{conflicts.length}</span>
            </button>
            <button 
              type="button"
              className={`diff-tab-btn tab-mod ${activeTab === 'modifications' ? 'active' : ''}`}
              onClick={() => setActiveTab('modifications')}
            >
              Modifications <span className="tab-count">{modifications.length}</span>
            </button>
            <button 
              type="button"
              className={`diff-tab-btn tab-add ${activeTab === 'additions' ? 'active' : ''}`}
              onClick={() => setActiveTab('additions')}
            >
              Additions <span className="tab-count">{additions.length}</span>
            </button>
            <button 
              type="button"
              className={`diff-tab-btn tab-rem ${activeTab === 'removals' ? 'active' : ''}`}
              onClick={() => setActiveTab('removals')}
            >
              Removals <span className="tab-count">{removals.length}</span>
            </button>
            <button 
              type="button"
              className={`diff-tab-btn tab-comm ${activeTab === 'common' ? 'active' : ''}`}
              onClick={() => setActiveTab('common')}
            >
              Common Content <span className="tab-count">{common.length}</span>
            </button>
          </div>

          {/* Detailed Differences List */}
          <div className="differences-list">
            {/* 1. CONFLICTS SECTION */}
            {(activeTab === 'all' || activeTab === 'conflicts') && conflicts.length > 0 && (
              <div className="diff-section-group">
                <div className="diff-section-title-row">
                  <div className="diff-section-heading">
                    <ShieldAlert size={18} className="text-danger" />
                    <h2>Conflicting Evidence</h2>
                    <span className="section-badge danger">{conflicts.length}</span>
                  </div>
                  <p className="diff-section-sub">
                    Direct contradictions or incompatible values asserted for the exact same metric or attribute.
                  </p>
                </div>

                <div className="diff-cards-stack">
                  {conflicts.map((item) => (
                    <GlassPanel key={item.id} className="diff-item-card card-conflict">
                      <div className="diff-card-header">
                        <div className="diff-card-badge-row">
                          <span className="diff-type-badge conflict">Conflict Detected</span>
                          <span className="diff-topic-name">{item.topic}</span>
                        </div>
                      </div>

                      {/* Before / After Comparison Grid */}
                      <div className="diff-columns-grid">
                        <div className="diff-column doc-a-column">
                          <div className="column-header">
                            <span className="column-doc-pill a">Document A</span>
                            <span className="column-doc-sub">Asserted specification</span>
                          </div>
                          <div className="column-statement doc-a-statement">
                            <p>{item.document_a}</p>
                          </div>
                          <SourceEvidence sources={item.sources_a} label="Doc A Evidence" variant="doc-a" />
                        </div>

                        <div className="diff-columns-divider">
                          <div className="divider-icon">≠</div>
                        </div>

                        <div className="diff-column doc-b-column">
                          <div className="column-header">
                            <span className="column-doc-pill b">Document B</span>
                            <span className="column-doc-sub">Contradictory claim</span>
                          </div>
                          <div className="column-statement doc-b-statement">
                            <p>{item.document_b}</p>
                          </div>
                          <SourceEvidence sources={item.sources_b} label="Doc B Evidence" variant="doc-b" />
                        </div>
                      </div>

                      {item.explanation && (
                        <div className="diff-card-explanation conflict-explanation">
                          <Info size={14} className="shrink-0 text-danger" />
                          <p>{item.explanation}</p>
                        </div>
                      )}
                    </GlassPanel>
                  ))}
                </div>
              </div>
            )}

            {/* 2. MODIFICATIONS SECTION */}
            {(activeTab === 'all' || activeTab === 'modifications') && modifications.length > 0 && (
              <div className="diff-section-group">
                <div className="diff-section-title-row">
                  <div className="diff-section-heading">
                    <AlertTriangle size={18} className="text-warning" />
                    <h2>Modifications & Revisions</h2>
                    <span className="section-badge warning">{modifications.length}</span>
                  </div>
                  <p className="diff-section-sub">
                    Specifications or policy statements that were revised, updated, or rescoped between documents.
                  </p>
                </div>

                <div className="diff-cards-stack">
                  {modifications.map((item) => (
                    <GlassPanel key={item.id} className="diff-item-card card-modification">
                      <div className="diff-card-header">
                        <div className="diff-card-badge-row">
                          <span className="diff-type-badge modification">Modified</span>
                          <span className="diff-topic-name">{item.topic}</span>
                        </div>
                      </div>

                      <div className="diff-columns-grid">
                        <div className="diff-column doc-a-column">
                          <div className="column-header">
                            <span className="column-doc-pill a">Document A</span>
                            <span className="column-doc-sub">Original version</span>
                          </div>
                          <div className="column-statement doc-a-statement">
                            <p>{item.document_a}</p>
                          </div>
                          <SourceEvidence sources={item.sources_a} label="Doc A Evidence" variant="doc-a" />
                        </div>

                        <div className="diff-columns-divider">
                          <ArrowRight size={16} className="text-warning" />
                        </div>

                        <div className="diff-column doc-b-column">
                          <div className="column-header">
                            <span className="column-doc-pill b">Document B</span>
                            <span className="column-doc-sub">Updated version</span>
                          </div>
                          <div className="column-statement doc-b-statement">
                            <p>{item.document_b}</p>
                          </div>
                          <SourceEvidence sources={item.sources_b} label="Doc B Evidence" variant="doc-b" />
                        </div>
                      </div>

                      {item.explanation && (
                        <div className="diff-card-explanation mod-explanation">
                          <Info size={14} className="shrink-0 text-warning" />
                          <p>{item.explanation}</p>
                        </div>
                      )}
                    </GlassPanel>
                  ))}
                </div>
              </div>
            )}

            {/* 3. ADDITIONS SECTION */}
            {(activeTab === 'all' || activeTab === 'additions') && additions.length > 0 && (
              <div className="diff-section-group">
                <div className="diff-section-title-row">
                  <div className="diff-section-heading">
                    <PlusCircle size={18} className="text-success" />
                    <h2>Additions</h2>
                    <span className="section-badge success">{additions.length}</span>
                  </div>
                  <p className="diff-section-sub">
                    New clauses, requirements, or specifications introduced in Document B that do not exist in Document A.
                  </p>
                </div>

                <div className="diff-cards-stack">
                  {additions.map((item) => (
                    <GlassPanel key={item.id} className="diff-item-card card-addition">
                      <div className="diff-card-header">
                        <div className="diff-card-badge-row">
                          <span className="diff-type-badge addition">+ Added in Document B</span>
                          <span className="diff-topic-name">{item.topic}</span>
                        </div>
                      </div>

                      <div className="single-content-box addition-content">
                        <p>{item.content}</p>
                      </div>

                      {item.explanation && (
                        <div className="diff-card-explanation addition-explanation">
                          <Info size={14} className="shrink-0 text-success" />
                          <p>{item.explanation}</p>
                        </div>
                      )}

                      <SourceEvidence sources={item.sources_b || item.sources} label="Document B Evidence" variant="doc-b" />
                    </GlassPanel>
                  ))}
                </div>
              </div>
            )}

            {/* 4. REMOVALS SECTION */}
            {(activeTab === 'all' || activeTab === 'removals') && removals.length > 0 && (
              <div className="diff-section-group">
                <div className="diff-section-title-row">
                  <div className="diff-section-heading">
                    <MinusCircle size={18} className="text-danger" />
                    <h2>Removals</h2>
                    <span className="section-badge danger">{removals.length}</span>
                  </div>
                  <p className="diff-section-sub">
                    Information present in Document A that was deleted or omitted from Document B.
                  </p>
                </div>

                <div className="diff-cards-stack">
                  {removals.map((item) => (
                    <GlassPanel key={item.id} className="diff-item-card card-removal">
                      <div className="diff-card-header">
                        <div className="diff-card-badge-row">
                          <span className="diff-type-badge removal">- Removed from Document B</span>
                          <span className="diff-topic-name">{item.topic}</span>
                        </div>
                      </div>

                      <div className="single-content-box removal-content">
                        <p>{item.content}</p>
                      </div>

                      {item.explanation && (
                        <div className="diff-card-explanation removal-explanation">
                          <Info size={14} className="shrink-0 text-danger" />
                          <p>{item.explanation}</p>
                        </div>
                      )}

                      <SourceEvidence sources={item.sources_a || item.sources} label="Document A Evidence" variant="doc-a" />
                    </GlassPanel>
                  ))}
                </div>
              </div>
            )}

            {/* 5. COMMON CONTENT SECTION */}
            {(activeTab === 'all' || activeTab === 'common') && common.length > 0 && (
              <div className="diff-section-group">
                <div className="diff-section-title-row">
                  <div className="diff-section-heading">
                    <CheckCircle2 size={18} className="text-secondary" />
                    <h2>Common & Unchanged Content</h2>
                    <span className="section-badge default">{common.length}</span>
                  </div>
                  <p className="diff-section-sub">
                    Statements and specifications that remain identical or semantically consistent across both documents.
                  </p>
                </div>

                <div className="diff-cards-stack">
                  {common.map((item) => (
                    <GlassPanel key={item.id} className="diff-item-card card-common">
                      <div className="diff-card-header">
                        <div className="diff-card-badge-row">
                          <span className="diff-type-badge common">Unchanged</span>
                          <span className="diff-topic-name">{item.topic}</span>
                        </div>
                      </div>

                      <div className="single-content-box common-content">
                        <p>{item.content}</p>
                      </div>

                      {item.explanation && (
                        <div className="diff-card-explanation common-explanation">
                          <Info size={14} className="shrink-0 text-tertiary" />
                          <p>{item.explanation}</p>
                        </div>
                      )}

                      <div className="common-sources-split">
                        <SourceEvidence sources={item.sources_a} label="Doc A Chunk" variant="doc-a" />
                        <SourceEvidence sources={item.sources_b} label="Doc B Chunk" variant="doc-b" />
                      </div>
                    </GlassPanel>
                  ))}
                </div>
              </div>
            )}

            {/* Empty Tab Message */}
            {activeTab !== 'all' && (
              (activeTab === 'conflicts' && conflicts.length === 0) ||
              (activeTab === 'modifications' && modifications.length === 0) ||
              (activeTab === 'additions' && additions.length === 0) ||
              (activeTab === 'removals' && removals.length === 0) ||
              (activeTab === 'common' && common.length === 0)
            ) && (
              <GlassPanel className="tab-empty-card">
                <CheckCircle2 size={24} className="text-success" />
                <h3>No {activeTab} detected</h3>
                <p>There are no items recorded under this category between Document A and Document B.</p>
              </GlassPanel>
            )}
          </div>

          {/* Grounding & Verification Panel */}
          <GroundingPanel 
            grounding={comparisonResult.grounding}
            provider={comparisonResult.provider}
            model={comparisonResult.model}
          />
        </div>
      )}

      {/* Initial Empty State */}
      {!isComparing && !comparisonResult && !errorMessage && (
        <GlassPanel className="compare-empty-state">
          <div className="empty-state-icon-circle">
            <GitCompare size={36} className="text-accent-primary" />
          </div>
          <h2 className="empty-state-title">Compare Two Documents</h2>
          <p className="empty-state-subtitle">
            Select two documents in the setup panel above to perform comprehensive side-by-side analysis.
          </p>

          <div className="empty-state-features-grid">
            <div className="empty-feature-item">
              <div className="feature-icon-box text-danger">
                <ShieldAlert size={18} />
              </div>
              <div className="feature-info">
                <h4>Conflicting Claims</h4>
                <p>Detect opposing values, contradictory policies, and conflicting numbers.</p>
              </div>
            </div>

            <div className="empty-feature-item">
              <div className="feature-icon-box text-warning">
                <AlertTriangle size={18} />
              </div>
              <div className="feature-info">
                <h4>Changed Specifications</h4>
                <p>Track modified parameters, revised dates, storage limits, and altered terms.</p>
              </div>
            </div>

            <div className="empty-feature-item">
              <div className="feature-icon-box text-success">
                <PlusCircle size={18} />
              </div>
              <div className="feature-info">
                <h4>Added Content</h4>
                <p>Highlight newly introduced sections and clauses present in Document B.</p>
              </div>
            </div>

            <div className="empty-feature-item">
              <div className="feature-icon-box text-secondary">
                <CheckCircle2 size={18} />
              </div>
              <div className="feature-info">
                <h4>Shared Information</h4>
                <p>Verify common content and unchanged baseline statements across versions.</p>
              </div>
            </div>
          </div>
        </GlassPanel>
      )}
    </div>
  );
};
