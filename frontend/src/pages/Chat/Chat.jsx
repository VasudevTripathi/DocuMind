import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  MessageSquare, Send, Plus, Trash2, Bot, User, 
  ChevronDown, ChevronUp, FileText, Loader2, Sparkles, AlertCircle 
} from 'lucide-react';
import { conversationService } from '../../services/conversationService';
import { documentService } from '../../services/documentService';
import './Chat.css';

export const Chat = () => {
  const [searchParams] = useSearchParams();
  const initialDocId = searchParams.get('documentId') || searchParams.get('docId') || '';

  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(initialDocId);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [activeConv, setActiveConv] = useState(null);
  
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [expandedSources, setExpandedSources] = useState({});

  const messagesEndRef = useRef(null);

  // Load documents for scoping selector
  useEffect(() => {
    async function loadDocs() {
      try {
        const docs = await documentService.getDocuments();
        setDocuments(docs || []);
      } catch (err) {
        console.error('Failed to load documents for chat selector:', err);
      }
    }
    loadDocs();
  }, []);

  // Load conversations when selected document changes
  useEffect(() => {
    async function fetchConversations() {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const list = await conversationService.getConversations(selectedDocId || null);
        setConversations(list || []);
        if (list && list.length > 0) {
          // If current active conversation is not in list, pick the first one
          if (!activeConvId || !list.some(c => c.id === activeConvId)) {
            setActiveConvId(list[0].id);
          }
        } else {
          setActiveConvId(null);
          setActiveConv(null);
        }
      } catch (err) {
        setErrorMessage(err.message);
      } finally {
        setIsLoading(false);
      }
    }
    fetchConversations();
  }, [selectedDocId]);

  // Load conversation detail and messages when activeConvId changes
  useEffect(() => {
    if (!activeConvId) {
      setActiveConv(null);
      return;
    }

    async function loadConversationDetail() {
      try {
        const detail = await conversationService.getConversation(activeConvId);
        setActiveConv(detail);
      } catch (err) {
        console.error('Failed to load conversation messages:', err);
        setErrorMessage(err.message);
      }
    }

    loadConversationDetail();
  }, [activeConvId]);

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeConv?.messages, isSending]);

  const handleCreateNewConversation = async () => {
    setErrorMessage(null);
    try {
      const newConv = await conversationService.createConversation(
        selectedDocId || null,
        'New Conversation'
      );
      setConversations(prev => [newConv, ...prev]);
      setActiveConvId(newConv.id);
    } catch (err) {
      setErrorMessage(err.message);
    }
  };

  const handleDeleteConversation = async (e, convId) => {
    e.stopPropagation();
    try {
      await conversationService.deleteConversation(convId);
      setConversations(prev => prev.filter(c => c.id !== convId));
      if (activeConvId === convId) {
        setActiveConvId(null);
        setActiveConv(null);
      }
    } catch (err) {
      setErrorMessage(err.message);
    }
  };

  const handleSendMessage = async (textToSend = null) => {
    const text = (textToSend || inputQuery).trim();
    if (!text || isSending) return;

    setErrorMessage(null);
    setInputQuery('');

    let convId = activeConvId;

    // If no conversation exists yet, automatically create one first
    if (!convId) {
      try {
        const newConv = await conversationService.createConversation(
          selectedDocId || null,
          text.slice(0, 35) + (text.length > 35 ? '...' : '')
        );
        convId = newConv.id;
        setActiveConvId(convId);
        setConversations(prev => [newConv, ...prev]);
      } catch (err) {
        setErrorMessage(err.message);
        return;
      }
    }

    // Optimistically append user message to local state
    const optimisticUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString()
    };

    setActiveConv(prev => prev ? {
      ...prev,
      messages: [...(prev.messages || []), optimisticUserMsg]
    } : {
      id: convId,
      title: text.slice(0, 35),
      messages: [optimisticUserMsg]
    });

    setIsSending(true);

    try {
      const assistantResponse = await conversationService.sendMessage(convId, text);
      
      // Update conversation detail with true assistant response
      setActiveConv(prev => ({
        ...prev,
        messages: [...(prev.messages || []).filter(m => m.id !== optimisticUserMsg.id), optimisticUserMsg, assistantResponse]
      }));

      // Update conversation title in list if this was first message
      setConversations(prev => prev.map(c => {
        if (c.id === convId && (c.title === 'New Conversation' || !c.title)) {
          return { ...c, title: text.slice(0, 40) };
        }
        return c;
      }));
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setIsSending(false);
    }
  };

  const toggleSourceExpand = (msgId) => {
    setExpandedSources(prev => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  return (
    <div className="chat-container">
      {/* Sidebar: Conversations & Document Scoping */}
      <div className="chat-sidebar">
        <div className="chat-sidebar-header">
          <div className="chat-sidebar-title">
            <MessageSquare size={18} className="text-accent-primary" />
            <span>Conversations</span>
          </div>
          <button 
            className="chat-send-btn" 
            style={{ width: '32px', height: '32px', borderRadius: 'var(--radius-sm)' }}
            onClick={handleCreateNewConversation}
            title="Start New Conversation"
          >
            <Plus size={16} />
          </button>
        </div>

        {/* Document Scoping Filter */}
        <div style={{ marginBottom: '8px' }}>
          <label style={{ fontSize: '11px', color: 'var(--text-tertiary)', display: 'block', marginBottom: '4px' }}>
            Document Context
          </label>
          <select 
            className="doc-filter-select"
            value={selectedDocId}
            onChange={(e) => setSelectedDocId(e.target.value)}
          >
            <option value="">All Documents (Library Wide)</option>
            {documents.map(d => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>

        {/* Conversation List */}
        <div className="conv-list">
          {isLoading ? (
            <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '12px' }}>
              <Loader2 size={16} className="animate-spin" style={{ margin: '0 auto 8px' }} />
              Loading conversations...
            </div>
          ) : conversations.length === 0 ? (
            <div style={{ padding: '24px 8px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '12px' }}>
              No conversations yet. Click "+" to start one.
            </div>
          ) : (
            conversations.map(conv => (
              <div 
                key={conv.id} 
                className={`conv-item ${activeConvId === conv.id ? 'active' : ''}`}
                onClick={() => setActiveConvId(conv.id)}
              >
                <div className="conv-info">
                  <span className="conv-title">{conv.title || 'Untitled Chat'}</span>
                  <span className="conv-meta">
                    <FileText size={10} />
                    {conv.document_name || (conv.document_id ? 'Document' : 'Library')}
                  </span>
                </div>
                <button 
                  className="conv-delete-btn"
                  onClick={(e) => handleDeleteConversation(e, conv.id)}
                  title="Delete conversation"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="chat-main">
        {/* Header */}
        <div className="chat-main-header">
          <div className="chat-header-info">
            <h2>{activeConv?.title || 'Document AI Assistant'}</h2>
            <div className="chat-header-scope">
              <Sparkles size={13} className="text-accent-secondary" />
              <span>
                {activeConv?.document_name
                  ? `Scoped to: ${activeConv.document_name}`
                  : (selectedDocId ? 'Scoped to selected document' : 'Grounded across full document library')}
              </span>
            </div>
          </div>
        </div>

        {/* Messages Scroll Area */}
        <div className="chat-messages-area">
          {errorMessage && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              color: '#ef4444',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <AlertCircle size={15} />
              <span>{errorMessage}</span>
            </div>
          )}

          {(!activeConv?.messages || activeConv.messages.length === 0) ? (
            <div className="empty-chat-state">
              <Bot size={40} className="text-accent-primary" style={{ margin: '0 auto 12px' }} />
              <h3 style={{ color: 'var(--text-primary)', marginBottom: '8px' }}>Ask DocuMind AI</h3>
              <p style={{ fontSize: '13px' }}>
                Ask factual questions grounded strictly in your document chunks. You can ask follow-ups naturally.
              </p>

              <div className="suggested-prompts">
                <button 
                  className="suggested-prompt-btn"
                  onClick={() => handleSendMessage("What are the key findings or highlights in this document?")}
                >
                  "What are the key findings or highlights in this document?"
                </button>
                <button 
                  className="suggested-prompt-btn"
                  onClick={() => handleSendMessage("Summarize the main requirements or protocols.")}
                >
                  "Summarize the main requirements or protocols."
                </button>
                <button 
                  className="suggested-prompt-btn"
                  onClick={() => handleSendMessage("Are there any critical error thresholds or alerts mentioned?")}
                >
                  "Are there any critical error thresholds or alerts mentioned?"
                </button>
              </div>
            </div>
          ) : (
            activeConv.messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              const hasSources = !isUser && msg.sources && msg.sources.length > 0;
              const isExpanded = expandedSources[msg.id || idx];

              return (
                <div key={msg.id || idx} className={`message-row ${isUser ? 'user' : 'assistant'}`}>
                  <div className={`msg-avatar ${isUser ? 'user-avatar' : 'ai-avatar'}`}>
                    {isUser ? <User size={16} /> : <Bot size={16} />}
                  </div>

                  <div className="msg-bubble">
                    <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>

                    {/* Telemetry & Grounding Metadata Bar */}
                    {!isUser && (msg.provider || msg.model || msg.grounding) && (
                      <div className="msg-meta-bar">
                        {msg.grounding?.status && (
                          <span className={`grounding-badge ${msg.grounding.status.toLowerCase()}`}>
                            {msg.grounding.status.replace('_', ' ')}
                            {msg.grounding.confidence ? ` • ${Math.round(msg.grounding.confidence * 100)}%` : ''}
                          </span>
                        )}
                        {(msg.provider || msg.model) && (
                          <span className="provider-pill">
                            {msg.provider === 'gemini'
                              ? `Gemini (${msg.model || 'gemini-2.5-flash'})`
                              : msg.provider === 'openai'
                                ? `OpenAI (${msg.model || 'gpt-4o-mini'})`
                                : 'Local Fallback'}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Source Attribution Accordion */}
                    {hasSources && (
                      <div className="sources-container">
                        <button 
                          className="sources-toggle"
                          onClick={() => toggleSourceExpand(msg.id || idx)}
                        >
                          <span>{msg.sources.length} Grounded Source{msg.sources.length > 1 ? 's' : ''}</span>
                          {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                        </button>

                        {isExpanded && (
                          <div className="sources-list">
                            {msg.sources.map((src, sIdx) => (
                              <div key={sIdx} className="source-item">
                                <div className="source-header">
                                  <span>Chunk #{src.chunk_index} ({src.document_name || src.document_id})</span>
                                  <span className="source-score">Relevance: {(src.score || 0).toFixed(3)}</span>
                                </div>
                                {src.text && (
                                  <div className="source-preview">
                                    "{src.text.length > 180 ? src.text.slice(0, 180) + '...' : src.text}"
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {isSending && (
            <div className="message-row assistant">
              <div className="msg-avatar ai-avatar">
                <Bot size={16} />
              </div>
              <div className="msg-bubble" style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)' }}>
                <Loader2 size={14} className="animate-spin text-accent-primary" />
                <span style={{ fontSize: '12px' }}>Retrieving grounded context & answering...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="chat-input-bar">
          <textarea
            className="chat-textarea"
            placeholder="Ask a question or follow-up grounded in your documents..."
            rows={1}
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
          />
          <button 
            className="chat-send-btn" 
            onClick={() => handleSendMessage()}
            disabled={!inputQuery.trim() || isSending}
            title="Send Message (Enter)"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
