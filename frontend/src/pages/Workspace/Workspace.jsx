import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, FileText, Download, CheckSquare, RefreshCw, Trash2, 
  Sparkles, Layers, MessageSquare, BookOpen, AlertCircle, Send, 
  Copy, Check, Clock, Database, Tag
} from 'lucide-react';
import { GlassPanel } from '../../components/ui/GlassPanel';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { documentService } from '../../services/documentService';
import { conversationService } from '../../services/conversationService';
import './Workspace.css';

export const Workspace = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [document, setDocument] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  // Chat State
  const [conversation, setConversation] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isSending, setIsSending] = useState(false);
  const chatScrollRef = useRef(null);

  // Chunks search filter
  const [chunkFilter, setChunkFilter] = useState('');
  const [copiedChunkId, setCopiedChunkId] = useState(null);

  const loadDocumentData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [docData, chunksData] = await Promise.all([
        documentService.getDocumentById(id),
        documentService.getDocumentChunks(id)
      ]);
      setDocument(docData);
      setChunks(chunksData || []);

      // Attempt to load analysis if ready
      if (docData?.status === 'analyzed') {
        try {
          const analysisData = await documentService.getDocumentAnalysis(id);
          setAnalysis(analysisData);
        } catch {
          // Analysis may still be in progress
        }
      }
    } catch (err) {
      setError(err.message || 'Failed to load document details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      loadDocumentData();
    }
  }, [id]);

  // Poll if document is still pending or processing in background
  useEffect(() => {
    let timer;
    if (id && document && (document.status === 'processing' || document.status === 'pending')) {
      timer = setInterval(async () => {
        try {
          const updatedDoc = await documentService.getDocumentById(id);
          if (updatedDoc?.status === 'analyzed') {
            setDocument(updatedDoc);
            const [analysisData, chunksData] = await Promise.all([
              documentService.getDocumentAnalysis(id).catch(() => null),
              documentService.getDocumentChunks(id).catch(() => [])
            ]);
            if (analysisData) setAnalysis(analysisData);
            if (chunksData?.length) setChunks(chunksData);
            clearInterval(timer);
          } else if (updatedDoc?.status === 'failed') {
            setDocument(updatedDoc);
            clearInterval(timer);
          }
        } catch {
          // Continue polling silently
        }
      }, 2500);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [id, document?.status]);

  // Initialize or fetch conversation for this document
  useEffect(() => {
    const initChat = async () => {
      if (!id || !document) return;
      try {
        const conv = await conversationService.createConversation(
          id,
          `Workspace Chat - ${document.name}`
        );
        setConversation(conv);
        setChatMessages(conv.messages || []);
      } catch (err) {
        console.error('Failed to init workspace conversation:', err);
      }
    };
    initChat();
  }, [id, document]);

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [chatMessages, isSending]);

  const handleSendMessage = async (textToSend) => {
    const text = (textToSend || inputQuery).trim();
    if (!text || isSending || !conversation) return;

    setInputQuery('');
    const userMsg = { id: `local-${Date.now()}`, role: 'user', content: text };
    setChatMessages((prev) => [...prev, userMsg]);
    setIsSending(true);

    try {
      const assistantMsg = await conversationService.sendMessage(conversation.id, text);
      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${err.message || 'Failed to generate response.'}`
        }
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleReprocess = async () => {
    try {
      await documentService.processDocument(id);
      loadDocumentData();
    } catch (err) {
      alert(`Reprocess failed: ${err.message}`);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete "${document.name}"?`)) return;
    try {
      await documentService.deleteDocument(id);
      navigate('/documents');
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const copyChunk = (chunkId, text) => {
    navigator.clipboard.writeText(text);
    setCopiedChunkId(chunkId);
    setTimeout(() => setCopiedChunkId(null), 2000);
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const filteredChunks = chunks.filter((c) => 
    !chunkFilter || c.text.toLowerCase().includes(chunkFilter.toLowerCase())
  );

  if (isLoading) {
    return (
      <div className="workspace-container">
        <GlassPanel style={{ padding: 'var(--space-12)', textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto var(--space-4)' }} />
          <p className="text-secondary">Loading document workspace...</p>
        </GlassPanel>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="workspace-container">
        <GlassPanel style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
          <AlertCircle size={40} className="text-danger" style={{ margin: '0 auto var(--space-3)' }} />
          <h2>Document Not Found</h2>
          <p className="text-secondary mb-4">{error || 'This document does not exist or has been deleted.'}</p>
          <Button variant="primary" onClick={() => navigate('/documents')}>
            <ArrowLeft size={16} /> Back to Documents
          </Button>
        </GlassPanel>
      </div>
    );
  }

  return (
    <div className="workspace-container">
      {/* Top Back & Quick Actions Bar */}
      <div className="workspace-top-bar">
        <button className="back-link-btn" onClick={() => navigate('/documents')}>
          <ArrowLeft size={16} /> Back to Documents
        </button>

        <div className="workspace-actions-group">
          <Button 
            variant="secondary" 
            size="sm"
            onClick={() => window.open(documentService.getDocumentFileUrl(document.id), '_blank')}
          >
            <Download size={14} /> Download Original
          </Button>
          <Button 
            variant="secondary" 
            size="sm"
            onClick={() => navigate('/compare')}
          >
            <CheckSquare size={14} /> Compare
          </Button>
          <Button 
            variant="secondary" 
            size="sm"
            onClick={handleReprocess}
          >
            <RefreshCw size={14} /> Reprocess
          </Button>
          <Button 
            variant="danger" 
            size="sm"
            onClick={handleDelete}
          >
            <Trash2 size={14} /> Delete
          </Button>
        </div>
      </div>

      {/* Document Header Glass Card */}
      <GlassPanel className="workspace-doc-header">
        <div className="doc-header-main">
          <div className="doc-title-wrapper">
            <div className="doc-file-icon">
              <FileText size={24} />
            </div>
            <div>
              <h1>{document.name}</h1>
              <div className="doc-meta-pills" style={{ marginTop: 'var(--space-2)' }}>
                <Badge variant={document.status === 'analyzed' ? 'success' : document.status === 'failed' ? 'danger' : 'warning'}>
                  {document.status}
                </Badge>
                <Badge variant="default">{document.category}</Badge>
                <span className="meta-pill-item">
                  <Database size={13} /> {chunks.length} Chunks
                </span>
                <span className="meta-pill-item">
                  <FileText size={13} /> {formatBytes(document.size_bytes)}
                </span>
                <span className="meta-pill-item">
                  <Clock size={13} /> {new Date(document.uploaded_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="workspace-tabs-nav">
          <button 
            className={`workspace-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <Sparkles size={16} /> Executive Insights
          </button>
          <button 
            className={`workspace-tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <MessageSquare size={16} /> AI Copilot Chat
          </button>
          <button 
            className={`workspace-tab-btn ${activeTab === 'chunks' ? 'active' : ''}`}
            onClick={() => setActiveTab('chunks')}
          >
            <Layers size={16} /> Chunks & Vectors ({chunks.length})
          </button>
        </div>
      </GlassPanel>

      {/* Tab 1: Executive Insights */}
      {activeTab === 'overview' && (
        <div className="overview-grid">
          <div className="overview-main-col">
            {/* Quota Exhausted Warning Banner */}
            {Boolean(
              analysis?.quota_exceeded 
              || analysis?.quotaExceeded 
              || analysis?.provider === 'quota_exhausted' 
              || (analysis?.summary && (analysis.summary.includes('quota limit') || analysis.summary.includes('429 RESOURCE_EXHAUSTED') || analysis.summary.includes('quota exceeded')))
            ) && (
              <div style={{
                backgroundColor: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                borderRadius: 'var(--radius-md, 8px)',
                padding: '12px 16px',
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px'
              }}>
                <AlertCircle size={20} style={{ color: '#ef4444', flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div style={{ fontWeight: 600, color: '#f87171', marginBottom: '4px', fontSize: '14px' }}>
                    Gemini API Daily Quota Limit Reached (429 RESOURCE_EXHAUSTED)
                  </div>
                  <div style={{ fontSize: '13px', lineHeight: 1.4, color: '#e2e8f0' }}>
                    Your Google AI Studio daily free request quota was exhausted. The summary and key findings below were extracted using <strong>local offline sentence heuristics</strong> rather than Gemini LLM synthesis.
                  </div>
                </div>
              </div>
            )}

            {/* AI Summary */}
            <GlassPanel className="insight-card">
              <div className="insight-card-header">
                <span className="insight-card-title">
                  <Sparkles size={18} className="text-accent-primary" /> AI Executive Summary
                </span>
              </div>
              <div className="summary-text-box">
                {analysis?.summary || (
                  <span className="text-tertiary">
                    {document.status === 'analyzed' 
                      ? 'No summary generated yet.' 
                      : 'Document is currently processing. AI summary will appear once indexing is complete.'}
                  </span>
                )}
              </div>
            </GlassPanel>

            {/* Key Findings */}
            <GlassPanel className="insight-card">
              <div className="insight-card-header">
                <span className="insight-card-title">
                  <BookOpen size={18} className="text-warning" /> Key Findings & Takeaways
                </span>
                <span className="text-secondary text-xs">
                  {(analysis?.findings || analysis?.keyFindings || []).length} extracted points
                </span>
              </div>
              <div className="findings-list">
                {(analysis?.findings || analysis?.keyFindings) && (analysis.findings || analysis.keyFindings).length > 0 ? (
                  (analysis.findings || analysis.keyFindings).map((f, i) => (
                    <div key={i} className="finding-item">
                      <span className="finding-bullet">•</span>
                      <span className="finding-text">{typeof f === 'object' && f !== null ? (f.text || f.finding || JSON.stringify(f)) : String(f)}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-secondary text-sm">No specific key findings extracted yet.</p>
                )}
              </div>
            </GlassPanel>

            {/* Entities */}
            {analysis?.entities && analysis.entities.length > 0 && (
              <GlassPanel className="insight-card">
                <div className="insight-card-header">
                  <span className="insight-card-title">
                    <Tag size={18} className="text-accent-secondary" /> Named Entities & Concepts
                  </span>
                </div>
                <div className="entities-cloud-box">
                  {analysis.entities.map((e, idx) => (
                    <span key={idx} className="entity-tag">
                      <span>{typeof e === 'object' && e !== null ? (e.name || e.text || '') : String(e)}</span>
                      <span className="entity-type-badge">{e.entity_type || e.type || 'CONCEPT'}</span>
                    </span>
                  ))}
                </div>
              </GlassPanel>
            )}
          </div>

          {/* Sidebar Metadata */}
          <div className="overview-side-col">
            <GlassPanel className="insight-card">
              <span className="insight-card-title">Document Intelligence</span>
              <div className="details-list">
                <div className="details-row">
                  <span className="details-label">Format</span>
                  <span className="details-val">{(document.file_type || document.type || 'TXT').toUpperCase()}</span>
                </div>
                <div className="details-row">
                  <span className="details-label">Category</span>
                  <span className="details-val">{document.category || 'General'}</span>
                </div>
                <div className="details-row">
                  <span className="details-label">Total Chunks</span>
                  <span className="details-val">{chunks.length}</span>
                </div>
                <div className="details-row">
                  <span className="details-label">Estimated Words</span>
                  <span className="details-val">
                    {chunks.reduce((acc, c) => acc + (c.word_count || 0), 0).toLocaleString()}
                  </span>
                </div>
                <div className="details-row">
                  <span className="details-label">Confidence</span>
                  <span className="details-val">
                    {(analysis?.classification_confidence ?? analysis?.classificationConfidence) != null
                      ? `${Math.round((analysis.classification_confidence ?? analysis.classificationConfidence) * 100)}%` 
                      : 'N/A'}
                  </span>
                </div>
                <div className="details-row">
                  <span className="details-label">MIME Type</span>
                  <span className="details-val">{document.mime_type || 'application/pdf'}</span>
                </div>
                <div className="details-row">
                  <span className="details-label">AI Engine</span>
                  <span className="details-val" style={{
                    color: Boolean(analysis?.quota_exceeded || analysis?.quotaExceeded || analysis?.provider === 'quota_exhausted') ? '#f87171' : 'inherit',
                    fontWeight: Boolean(analysis?.quota_exceeded || analysis?.quotaExceeded || analysis?.provider === 'quota_exhausted') ? 600 : 400
                  }}>
                    {Boolean(analysis?.quota_exceeded || analysis?.quotaExceeded || analysis?.provider === 'quota_exhausted')
                      ? 'Local Fallback (Quota Exceeded)'
                      : (analysis?.provider === 'gemini' ? 'Google Gemini' : 'Offline Rules')}
                  </span>
                </div>
              </div>
              <Button 
                variant="primary" 
                style={{ marginTop: 'var(--space-2)' }}
                onClick={() => setActiveTab('chat')}
              >
                <MessageSquare size={14} /> Ask Copilot About This Doc
              </Button>
            </GlassPanel>
          </div>
        </div>
      )}

      {/* Tab 2: AI Copilot Chat Scoped to This Document */}
      {activeTab === 'chat' && (
        <div className="workspace-chat-container">
          <div className="workspace-chat-messages" ref={chatScrollRef}>
            {chatMessages.length === 0 ? (
              <div style={{ textAlign: 'center', margin: 'auto', color: 'var(--text-tertiary)' }}>
                <Sparkles size={32} className="text-accent-primary" style={{ margin: '0 auto 12px' }} />
                <h3>Ask anything about {document.name}</h3>
                <p className="text-sm">Powered by Google Gemini 2.5 Flash and grounded strictly in this document.</p>
              </div>
            ) : (
              chatMessages.map((msg, i) => (
                <div key={msg.id || i} className={`workspace-chat-msg ${msg.role}`}>
                  <div className={`chat-avatar ${msg.role === 'user' ? 'user-avatar' : 'ai-avatar'}`}>
                    {msg.role === 'user' ? 'U' : 'AI'}
                  </div>
                  <div className="chat-bubble">
                    <p style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
                    {msg.sources && msg.sources.length > 0 && (
                      <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--text-tertiary)' }}>
                        <span>Grounded in {msg.sources.length} document chunk(s)</span>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {isSending && (
              <div className="workspace-chat-msg assistant">
                <div className="chat-avatar ai-avatar">AI</div>
                <div className="chat-bubble">
                  <span className="text-secondary text-sm">Thinking & verifying citations...</span>
                </div>
              </div>
            )}
          </div>

          {/* Quick prompt suggestions */}
          <div className="quick-prompts-bar">
            <button className="quick-prompt-chip" onClick={() => handleSendMessage('summarize this document')}>
              ✨ Summarize this document
            </button>
            <button className="quick-prompt-chip" onClick={() => handleSendMessage('What are the key findings or highlights?')}>
              💡 Key findings & highlights
            </button>
            <button className="quick-prompt-chip" onClick={() => handleSendMessage('List all units and topics covered')}>
              📋 Units & topics
            </button>
          </div>

          {/* Input Bar */}
          <form 
            className="workspace-chat-input-bar"
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
          >
            <input 
              type="text"
              className="chat-text-input"
              placeholder={`Ask a question grounded in ${document.name}...`}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              disabled={isSending}
            />
            <Button variant="primary" type="submit" disabled={!inputQuery.trim() || isSending}>
              <Send size={15} />
            </Button>
          </form>
        </div>
      )}

      {/* Tab 3: Chunks & Vectors Explorer */}
      {activeTab === 'chunks' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
            <input 
              type="text"
              className="chat-text-input"
              style={{ maxWidth: '360px' }}
              placeholder="Search within chunks text..."
              value={chunkFilter}
              onChange={(e) => setChunkFilter(e.target.value)}
            />
            <span className="text-secondary text-sm">
              Showing {filteredChunks.length} of {chunks.length} chunks
            </span>
          </div>

          <div className="chunks-explorer-list">
            {filteredChunks.map((chunk) => (
              <GlassPanel key={chunk.id} className="chunk-item-card">
                <div className="chunk-item-header">
                  <span>
                    <strong>Chunk #{chunk.chunk_index + 1}</strong> • {chunk.word_count} words
                    {chunk.page_number && ` • Page ${chunk.page_number}`}
                  </span>
                  <button 
                    className="back-link-btn"
                    onClick={() => copyChunk(chunk.id, chunk.text)}
                  >
                    {copiedChunkId === chunk.id ? (
                      <span className="text-success" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Check size={14} /> Copied
                      </span>
                    ) : (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Copy size={14} /> Copy Chunk
                      </span>
                    )}
                  </button>
                </div>
                <div className="chunk-text-box">
                  {chunk.text}
                </div>
              </GlassPanel>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
