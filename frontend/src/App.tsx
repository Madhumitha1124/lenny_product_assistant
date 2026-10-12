import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DOMPurify from 'dompurify';
import {
  Plus, MessageSquare, Trash2, Send, ChevronDown, ChevronUp,
  BookOpen, Copy, Check, Download, X, Zap,
  AlertCircle, ExternalLink, RefreshCw, FileText,
} from 'lucide-react';
import './styles/main.css';
import * as api from './services/api';
import type { Session, Message, ModelInfo, Artifact, SourceCitation } from './types';

// ── Suggested prompts ──────────────────────────────────────────────────────────
const SUGGESTED_PROMPTS = [
  { icon: '🎯', text: 'How do successful products find product-market fit?' },
  { icon: '🚀', text: 'What makes a strong user onboarding experience?' },
  { icon: '📈', text: 'How should an early-stage startup prioritize growth?' },
  { icon: '✍️', text: 'Generate an essay about building products users love.' },
];

// ── Source Citations component ─────────────────────────────────────────────────
function SourcesPanel({ sources }: { sources: SourceCitation[] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;
  return (
    <div className="sources-panel">
      <button className="sources-toggle" onClick={() => setOpen(!open)}>
        <BookOpen size={13} />
        <span className="sources-toggle-label">{sources.length} source{sources.length > 1 ? 's' : ''} cited</span>
        {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>
      {open && (
        <div className="sources-list">
          {sources.map((s) => (
            <div key={s.source_id} className="source-item">
              <div className="source-title">
                {s.title}
                {s.is_demo && <span className="demo-badge">DEMO</span>}
              </div>
              {s.author && <div className="source-author">By {s.author}</div>}
              <div className="source-excerpt">"{s.excerpt}"</div>
              {s.source_url && (
                <a href={s.source_url} target="_blank" rel="noopener noreferrer"
                  style={{ fontSize: 11, color: 'var(--text-accent)', display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
                  <ExternalLink size={10} /> View source
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Copy button ────────────────────────────────────────────────────────────────
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button className="btn-action" onClick={handleCopy}>
      {copied ? <Check size={11} /> : <Copy size={11} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

// ── Message component ──────────────────────────────────────────────────────────
function MessageItem({ msg, onOpenArtifact }: {
  msg: Message;
  onOpenArtifact: (id: string) => void;
}) {
  if (msg.role === 'user') {
    return (
      <div className="message-wrapper user">
        <div className="message-bubble">{msg.content}</div>
      </div>
    );
  }
  return (
    <div className="message-wrapper assistant">
      <div className="assistant-content">
        <div className="assistant-header">
          <div className="assistant-avatar">🤖</div>
          <span className="assistant-name">Lenny Assistant</span>
          {msg.model && (
            <span className="assistant-model-tag">{msg.provider} / {msg.model}</span>
          )}
        </div>
        <div className="markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
        </div>
        <SourcesPanel sources={msg.sources || []} />
        {msg.artifact_id && (
          <button className="btn-action" style={{ marginTop: 8 }} onClick={() => onOpenArtifact(msg.artifact_id!)}>
            <FileText size={11} /> View Artifact
          </button>
        )}
        <div className="message-actions">
          <CopyButton text={msg.content} />
        </div>
      </div>
    </div>
  );
}

// ── Artifact Viewer ────────────────────────────────────────────────────────────
function ArtifactViewer({ artifact, onClose }: { artifact: Artifact; onClose: () => void }) {
  const [tab, setTab] = useState<'preview' | 'source'>('preview');
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(artifact.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const ext = artifact.artifact_type === 'html' || artifact.artifact_type === 'landing_page' ? 'html' : 'md';
    const blob = new Blob([artifact.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${artifact.title}.${ext}`; a.click();
    URL.revokeObjectURL(url);
  };

  const isHtml = artifact.artifact_type === 'html' || artifact.artifact_type === 'landing_page';
  const sanitizedHtml = isHtml
    ? DOMPurify.sanitize(artifact.content, { USE_PROFILES: { html: true } })
    : '';
  const contentSecurityPolicy =
    '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; font-src data:">';
  const previewHtml = /<head(?:\s[^>]*)?>/i.test(sanitizedHtml)
    ? sanitizedHtml.replace(/<head(?:\s[^>]*)?>/i, (head) => `${head}${contentSecurityPolicy}`)
    : `<!doctype html><html><head>${contentSecurityPolicy}</head><body>${sanitizedHtml}</body></html>`;

  return (
    <div className="artifact-panel">
      <div className="artifact-header">
        <span className="artifact-title">{artifact.title}</span>
        <span className="artifact-type-badge">{artifact.artifact_type}</span>
        <button className="btn-icon" onClick={onClose} title="Close artifact"><X size={14} /></button>
      </div>

      <div className="artifact-tabs">
        <button className={`artifact-tab ${tab === 'preview' ? 'active' : ''}`} onClick={() => setTab('preview')}>Preview</button>
        <button className={`artifact-tab ${tab === 'source' ? 'active' : ''}`} onClick={() => setTab('source')}>Source</button>
      </div>

      <div className="artifact-content">
        {tab === 'preview' ? (
          isHtml ? (
            /* Sandboxed iframe — no same-origin, no scripts, no allow-top-navigation */
            <iframe
              className="artifact-preview-iframe"
              sandbox=""
              referrerPolicy="no-referrer"
              srcDoc={previewHtml}
              title="Artifact preview"
            />
          ) : (
            <div className="artifact-scroll">
              <div className="markdown-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.content}</ReactMarkdown>
              </div>
            </div>
          )
        ) : (
          <div className="artifact-scroll">
            <pre className="artifact-source-code">{artifact.content}</pre>
          </div>
        )}
      </div>

      <div className="artifact-actions">
        <button className="btn-artifact-action" onClick={handleCopy}>
          {copied ? <Check size={12} /> : <Copy size={12} />} Copy
        </button>
        <button className="btn-artifact-action" onClick={handleDownload}>
          <Download size={12} /> Download
        </button>
      </div>
    </div>
  );
}

// ── Model Selector Modal ───────────────────────────────────────────────────────
function ModelSelector({ models, current, currentProvider, onSelect, onClose }: {
  models: ModelInfo[];
  current: string;
  currentProvider: string;
  onSelect: (provider: string, model: string) => void;
  onClose: () => void;
}) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-title">Select Model</div>
        <div className="model-list">
          {models.length === 0 && (
            <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: 12 }}>
              No models detected. Ensure Ollama is running with: <code>ollama serve</code>
            </div>
          )}
          {models.map((m) => (
            <div
              key={`${m.provider}-${m.id}`}
              className={`model-option ${!m.available ? 'unavailable' : ''} ${current === m.id && currentProvider === m.provider ? 'selected' : ''}`}
              onClick={() => { if (m.available) { onSelect(m.provider, m.id); onClose(); } }}
            >
              <div className="model-option-info">
                <div className="model-option-name">{m.name}</div>
                <div className="model-option-desc">{m.available ? m.description : '⚠ ' + m.description}</div>
              </div>
              <span className={`provider-tag ${m.provider}`}>{m.provider}</span>
            </div>
          ))}
        </div>
        <div className="modal-footer">
          <button className="btn-modal-close" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

// ── Ship30 Modal ───────────────────────────────────────────────────────────────
function Ship30Modal({ onGenerate, onClose, isLoading }: {
  onGenerate: (topic: string) => void;
  onClose: () => void;
  isLoading: boolean;
}) {
  const [topic, setTopic] = useState('');
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-title">✍️ Generate Ship 30 Essay</div>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 14, lineHeight: 1.5 }}>
          Generate a ~1,250-word Ship 30 for 30 style essay grounded in the knowledge base.
        </p>
        <textarea
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Essay topic, e.g. 'How to achieve product-market fit'"
          rows={3}
          style={{
            width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)', color: 'var(--text-primary)', fontFamily: 'var(--font)',
            fontSize: 13, padding: '10px 12px', resize: 'none', outline: 'none',
          }}
          onFocus={(e) => (e.target.style.borderColor = 'var(--border-accent)')}
          onBlur={(e) => (e.target.style.borderColor = 'var(--border)')}
        />
        <div className="modal-footer" style={{ marginTop: 12, gap: 8, display: 'flex' }}>
          <button className="btn-modal-close" onClick={onClose}>Cancel</button>
          <button
            onClick={() => topic.trim() && onGenerate(topic.trim())}
            disabled={!topic.trim() || isLoading}
            style={{
              padding: '7px 16px', background: 'rgba(168,85,247,0.2)', border: '1px solid rgba(168,85,247,0.4)',
              borderRadius: 'var(--radius-md)', color: '#c084fc', fontSize: 13, cursor: 'pointer',
              fontFamily: 'var(--font)', opacity: (!topic.trim() || isLoading) ? 0.5 : 1,
            }}
          >
            {isLoading ? 'Generating…' : 'Generate Essay'}
          </button>
        </div>
      </div>
    </div>
  );
}

function ArtifactModal({ onGenerate, onClose, isLoading }: {
  onGenerate: (prompt: string, title: string, artifactType: Artifact['artifact_type']) => void;
  onClose: () => void;
  isLoading: boolean;
}) {
  const [prompt, setPrompt] = useState('');
  const [title, setTitle] = useState('');
  const [artifactType, setArtifactType] = useState<Artifact['artifact_type']>('markdown');

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-title">Create an artifact</div>
        <label className="artifact-form-label" htmlFor="artifact-title">Title</label>
        <input
          id="artifact-title"
          className="artifact-form-input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Untitled artifact"
          maxLength={512}
        />
        <label className="artifact-form-label" htmlFor="artifact-type">Format</label>
        <select
          id="artifact-type"
          className="artifact-form-input"
          value={artifactType}
          onChange={(e) => setArtifactType(e.target.value as Artifact['artifact_type'])}
        >
          <option value="markdown">Markdown document</option>
          <option value="html">HTML/CSS preview</option>
          <option value="prd">Product requirements document</option>
          <option value="growth_plan">Growth plan</option>
          <option value="strategy">Strategy</option>
        </select>
        <label className="artifact-form-label" htmlFor="artifact-prompt">What should it contain?</label>
        <textarea
          id="artifact-prompt"
          className="artifact-form-input artifact-form-prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the document or code you want to generate."
          rows={4}
        />
        <div className="modal-footer">
          <button className="btn-modal-close" onClick={onClose}>Cancel</button>
          <button
            className="btn-artifact-generate"
            onClick={() => onGenerate(prompt.trim(), title.trim() || 'Untitled Artifact', artifactType)}
            disabled={!prompt.trim() || isLoading}
          >
            {isLoading ? 'Generating…' : 'Generate'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────────
export default function App() {
  // Sessions
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isCreatingSession, setIsCreatingSession] = useState(false);

  // Model selection
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('ollama');
  const [selectedModel, setSelectedModel] = useState('llama3.2:3b');
  const [showModelSelector, setShowModelSelector] = useState(false);

  // Chat state
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Artifact
  const [openArtifact, setOpenArtifact] = useState<Artifact | null>(null);

  // Ship30
  const [showShip30, setShowShip30] = useState(false);
  const [ship30Loading, setShip30Loading] = useState(false);
  const [showArtifactModal, setShowArtifactModal] = useState(false);
  const [artifactLoading, setArtifactLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ── Load data on mount ─────────────────────────────────────────────────────
  useEffect(() => {
    loadSessions();
    loadModels();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const loadSessions = async () => {
    try {
      const data = await api.getSessions();
      setSessions(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? `Could not load conversations: ${err.message}` : 'Could not load conversations');
    }
  };

  const loadModels = async () => {
    try {
      const data = await api.getModels();
      setModels(data.models);
      setSelectedProvider(data.default_provider);
      setSelectedModel(data.default_model);
    } catch (err: unknown) {
      setError(err instanceof Error ? `Could not load models: ${err.message}` : 'Could not load models');
    }
  };

  const loadMessages = async (sessionId: string) => {
    try {
      const data = await api.getMessages(sessionId);
      setMessages(data);
    } catch (err: unknown) {
      setMessages([]);
      setError(err instanceof Error ? `Could not load conversation: ${err.message}` : 'Could not load conversation');
    }
  };

  // ── Session actions ────────────────────────────────────────────────────────
  const handleNewChat = async () => {
    if (isCreatingSession) return;
    setError(null);
    setOpenArtifact(null);
    setInput('');
    setIsCreatingSession(true);
    try {
      const session = await api.createSession('New Chat', selectedProvider, selectedModel);
      setSessions((prev) => [session, ...prev.filter((item) => item.id !== session.id)]);
      setActiveSessionId(session.id);
      setMessages([]);
      textareaRef.current?.focus();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create a new chat');
    } finally {
      setIsCreatingSession(false);
    }
  };

  const handleSelectSession = async (id: string) => {
    setActiveSessionId(id);
    setError(null);
    setOpenArtifact(null);
    await loadMessages(id);
  };

  const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([]);
        setOpenArtifact(null);
        setError(null);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? `Could not delete conversation: ${err.message}` : 'Could not delete conversation');
    }
  };

  // ── Send message ───────────────────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return;
    const userText = input.trim();
    setInput('');
    setError(null);
    setIsLoading(true);

    // Optimistic user message
    const tempMsg: Message = {
      id: `temp-${Date.now()}`, session_id: activeSessionId || '', role: 'user',
      content: userText, sources: [], created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempMsg]);

    try {
      const response = await api.sendChat({
        session_id: activeSessionId ?? undefined,
        message: userText,
        provider: selectedProvider,
        model: selectedModel,
      });

      // Update session list
      if (!activeSessionId || !sessions.find((s) => s.id === response.session_id)) {
        setActiveSessionId(response.session_id);
        await loadSessions();
      } else {
        setActiveSessionId(response.session_id);
      }

      // Load full message history (includes real IDs)
      await loadMessages(response.session_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to send message';
      setError(msg);
      setMessages((prev) => prev.filter((m) => m.id !== tempMsg.id));
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, activeSessionId, selectedProvider, selectedModel, sessions]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
  };

  // ── Open artifact ──────────────────────────────────────────────────────────
  const handleOpenArtifact = async (id: string) => {
    try {
      const artifact = await api.getArtifact(id);
      setOpenArtifact(artifact);
    } catch {
      setError('Failed to load artifact');
    }
  };

  // ── Ship 30 ───────────────────────────────────────────────────────────────
  const handleShip30 = async (topic: string) => {
    setShip30Loading(true);
    setShowShip30(false);
    try {
      const response = await api.generateShip30({
        topic,
        session_id: activeSessionId ?? undefined,
        provider: selectedProvider,
        model: selectedModel,
      });
      const artifact = await api.getArtifact(response.artifact_id);
      setOpenArtifact(artifact);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Essay generation failed';
      setError(msg);
    } finally {
      setShip30Loading(false);
    }
  };

  const handleGenerateArtifact = async (
    prompt: string,
    title: string,
    artifactType: Artifact['artifact_type'],
  ) => {
    setArtifactLoading(true);
    setShowArtifactModal(false);
    try {
      const generated = await api.createArtifact(
        prompt,
        artifactType,
        title,
        activeSessionId ?? undefined,
        selectedProvider,
        selectedModel,
      );
      setOpenArtifact(await api.getArtifact(generated.id));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Artifact generation failed');
    } finally {
      setArtifactLoading(false);
    }
  };

  // ── Current model display ──────────────────────────────────────────────────
  const currentModel = models.find((m) => m.id === selectedModel && m.provider === selectedProvider);
  const modelAvailable = currentModel?.available ?? false;

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return (
    <div className="app-layout">
      {/* ── Sidebar ─────────────────────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">📊</div>
          <div>
            <div className="sidebar-logo-text">Lenny Assistant</div>
            <div className="sidebar-logo-sub">Product Growth AI</div>
          </div>
        </div>

        <div className="sidebar-actions">
          <button className="btn-new-chat" onClick={handleNewChat} disabled={isCreatingSession} id="btn-new-chat">
            <Plus size={15} /> New Chat
          </button>
        </div>

        <div className="sidebar-section-label">Conversations</div>

        <div className="sidebar-sessions">
          {sessions.length === 0 ? (
            <div className="empty-sessions">Start a conversation to see your history here.</div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.id}
                className={`session-item ${s.id === activeSessionId ? 'active' : ''}`}
                onClick={() => handleSelectSession(s.id)}
                id={`session-${s.id}`}
              >
                <MessageSquare size={13} style={{ flexShrink: 0, color: 'var(--text-muted)' }} />
                <span className="session-title">{s.title}</span>
                <button
                  className="session-delete"
                  onClick={(e) => handleDeleteSession(s.id, e)}
                  title="Delete session"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="sidebar-footer">
          <div className="kb-panel">
            <div className="kb-badge">
              <BookOpen size={11} />
              <span>Knowledge Base Active</span>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main Chat ─────────────────────────────────────────────────────────── */}
      <main className="main-area">
        {/* Header */}
        <div className="chat-header">
          <div className="chat-header-left">
            <span className="chat-title">
              {activeSession?.title ?? 'The Lenny Growth Assistant'}
            </span>
          </div>
          <div className="chat-header-right">
            <button
              className="model-badge"
              onClick={() => { loadModels(); setShowModelSelector(true); }}
              id="btn-model-selector"
              title="Switch model"
            >
              <span className={`status-dot ${isLoading ? 'loading' : modelAvailable ? '' : 'offline'}`} />
              {selectedProvider} / {selectedModel}
              <ChevronDown size={12} />
            </button>
            <button className="btn-icon" onClick={loadModels} title="Refresh models">
              <RefreshCw size={14} />
            </button>
          </div>
        </div>

        {/* Chat body */}
        <div className="chat-body" id="chat-body">
          {messages.length === 0 && !isLoading ? (
            <div className="welcome">
              <div className="welcome-icon">📊</div>
              <h1>The Lenny Growth Assistant</h1>
              <p className="welcome-subtitle">
                Turn product knowledge into your next growth breakthrough.
                Grounded in Lenny's Podcast &amp; Newsletter insights.
              </p>
              <div className="suggested-prompts">
                {SUGGESTED_PROMPTS.map((p, i) => (
                  <button
                    key={i}
                    className="prompt-card"
                    onClick={() => { setInput(p.text); textareaRef.current?.focus(); }}
                    id={`suggested-prompt-${i}`}
                  >
                    <span className="prompt-card-icon">{p.icon}</span>
                    {p.text}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages-container">
              {messages.map((msg) => (
                <MessageItem key={msg.id} msg={msg} onOpenArtifact={handleOpenArtifact} />
              ))}
              {isLoading && (
                <div className="loading-message">
                  <div className="assistant-avatar" style={{ width: 24, height: 24, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, var(--accent), #a855f7)', fontSize: 12, flexShrink: 0 }}>🤖</div>
                  <div className="typing-indicator">
                    <div className="typing-dot" />
                    <div className="typing-dot" />
                    <div className="typing-dot" />
                  </div>
                </div>
              )}
              {error && (
                <div className="error-banner" style={{ margin: '8px 16px' }}>
                  <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>{error}</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Composer */}
        <div className="composer-area">
          {error && messages.length === 0 && (
            <div className="error-banner" style={{ marginBottom: 8 }}>
              <AlertCircle size={14} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}
          <div className="composer-wrapper">
            <textarea
              ref={textareaRef}
              className="composer-textarea"
              placeholder="Ask about product growth, onboarding, PMF, metrics…"
              value={input}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={1}
              id="chat-input"
            />
            <div className="composer-footer">
              <div className="composer-hints">
                <span>Enter to send</span>
                <span>·</span>
                <span>Shift+Enter for new line</span>
              </div>
              <div className="composer-actions">
                <button
                  className="btn-create-artifact"
                  onClick={() => setShowArtifactModal(true)}
                  disabled={isLoading || ship30Loading || artifactLoading}
                  id="btn-create-artifact"
                  title="Create a document or HTML preview"
                >
                  <FileText size={12} />
                  {artifactLoading ? 'Generating…' : 'Artifact'}
                </button>
                <button
                  className="btn-ship30"
                  onClick={() => setShowShip30(true)}
                  disabled={isLoading || ship30Loading}
                  id="btn-ship30"
                  title="Generate Ship 30 for 30 essay"
                >
                  <Zap size={12} />
                  {ship30Loading ? 'Generating…' : 'Ship 30'}
                </button>
                <button
                  className="btn-send"
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                  id="btn-send"
                  title="Send message"
                >
                  <Send size={15} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ── Artifact Viewer ──────────────────────────────────────────────────── */}
      {openArtifact && (
        <ArtifactViewer artifact={openArtifact} onClose={() => setOpenArtifact(null)} />
      )}

      {/* ── Modals ───────────────────────────────────────────────────────────── */}
      {showModelSelector && (
        <ModelSelector
          models={models}
          current={selectedModel}
          currentProvider={selectedProvider}
          onSelect={(p, m) => { setSelectedProvider(p); setSelectedModel(m); }}
          onClose={() => setShowModelSelector(false)}
        />
      )}

      {showShip30 && (
        <Ship30Modal
          onGenerate={handleShip30}
          onClose={() => setShowShip30(false)}
          isLoading={ship30Loading}
        />
      )}

      {showArtifactModal && (
        <ArtifactModal
          onGenerate={handleGenerateArtifact}
          onClose={() => setShowArtifactModal(false)}
          isLoading={artifactLoading}
        />
      )}
    </div>
  );
}
