import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  BrainCircuit, PlusSquare, MessageSquare, FileText, Settings,
  Mic, MicOff, Send, Trash2, ChevronLeft, Sun, Moon, Pin, Database,
  Minimize2, Maximize2
} from 'lucide-react';
import axios from 'axios';
import { getCurrentWindow } from '@tauri-apps/api/window';
import './index.css';

const API = 'http://localhost:8000/api';
const getUserId = () => {
  let id = localStorage.getItem('omni_uid');
  if (!id) { id = `u_${Date.now()}`; localStorage.setItem('omni_uid', id); }
  return id;
};

// ─── Types ───────────────────────────────────────────────────────────────────
interface Msg {
  id: string; role: 'user' | 'assistant';
  content: string; created_at: string;
  approval_request?: { action_key: string; session_id: string; original_message: string } | null;
  approvalState?: 'pending' | 'approved' | 'denied';
}
interface Session { id: string; title: string; }
type Page = 'chat' | 'settings' | 'pdf' | 'memory';

// ─── ApprovalCard ─────────────────────────────────────────────────────────────
function ApprovalCard({ msg, onDecide }: { msg: Msg; onDecide: (key: string, approved: boolean) => void }) {
  if (!msg.approval_request) return null;
  const { action_key } = msg.approval_request;
  if (msg.approvalState && msg.approvalState !== 'pending') {
    return (
      <div className="approval-card">
        <div className={`approval-decided ${msg.approvalState}`}>
          {msg.approvalState === 'approved' ? '✅ Action approved and executed.' : '❌ Action denied.'}
        </div>
      </div>
    );
  }
  return (
    <div className="approval-card">
      <div className="approval-card-title">⚠️ Action Requires Your Approval</div>
      <div className="approval-card-desc">
        <code style={{ fontSize: '0.78rem', background: 'rgba(99,110,123,0.2)', padding: '4px 8px', borderRadius: '4px', display: 'block', marginBottom: 8 }}>
          {action_key}
        </code>
        Do you want to allow this action?
      </div>
      <div className="approval-btns">
        <button className="btn-approve" onClick={() => onDecide(action_key, true)}>✓ Yes, Allow</button>
        <button className="btn-deny" onClick={() => onDecide(action_key, false)}>✗ No, Cancel</button>
      </div>
    </div>
  );
}

// ─── MessageBubble ────────────────────────────────────────────────────────────
function MessageBubble({ msg, onDecide }: { msg: Msg; onDecide: (key: string, approved: boolean) => void }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`msg-row ${msg.role}`}>
      <div className="msg-avatar">{isUser ? '👤' : '🤖'}</div>
      <div>
        <div className={`msg-bubble`}>
          {isUser ? (
            <span>{msg.content}</span>
          ) : (
            <ReactMarkdown
              components={{
                code({ node, className, children, ...props }: any) {
                  const match = /language-(\w+)/.exec(className || '');
                  const inline = !match;
                  return !inline ? (
                    <SyntaxHighlighter style={oneDark as any} language={match![1]} PreTag="div">
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>{children}</code>
                  );
                },
                a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>,
              }}
            >
              {msg.content}
            </ReactMarkdown>
          )}
        </div>
        {msg.approval_request && <ApprovalCard msg={msg} onDecide={onDecide} />}
      </div>
    </div>
  );
}

// ─── VoiceButton ─────────────────────────────────────────────────────────────
function VoiceButton({ onTranscript, disabled, isListening }: { onTranscript: (t: string) => void; disabled: boolean; isListening: (state: boolean) => void }) {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const toggle = async () => {
    if (recording) {
      mediaRef.current?.stop();
      setRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = e => chunksRef.current.push(e.data);
      mr.onstop = async () => {
        setTranscribing(true);
        isListening(false);
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const form = new FormData();
        form.append('audio', blob, 'audio.webm');
        try {
          const res = await axios.post(`${API}/voice/transcribe`, form, { headers: { 'Content-Type': 'multipart/form-data' } });
          if (res.data.text) onTranscript(res.data.text);
        } catch { /* silently fail */ }
        setTranscribing(false);
        stream.getTracks().forEach(t => t.stop());
      };
      mr.start();
      mediaRef.current = mr;
      setRecording(true);
      isListening(true);
    } catch { alert('Microphone access denied or unavailable.'); }
  };

  return (
    <button className={`icon-btn mic ${recording ? 'recording' : ''}`} onClick={toggle} disabled={disabled || transcribing} title={recording ? 'Stop recording' : 'Voice input'}>
      {transcribing ? <span style={{fontSize: '0.65rem', fontWeight: 'bold'}}>...</span> : recording ? <MicOff size={16} /> : <Mic size={16} />}
    </button>
  );
}

// ─── SettingsPage ─────────────────────────────────────────────────────────────
function SettingsPage({ theme, onThemeToggle }: { theme: string; onThemeToggle: () => void }) {
  const [voiceStatus, setVoiceStatus] = useState<{ available: boolean } | null>(null);
  useEffect(() => {
    axios.get(`${API}/voice/status`).then(r => setVoiceStatus(r.data)).catch(() => {});
  }, []);

  return (
    <div className="settings-page">
      <h1>⚙️ Settings</h1>

      <div className="settings-card">
        <h3>🎨 Appearance</h3>
        <div className="settings-row">
          <div>
            <div className="settings-label">Theme</div>
            <div className="settings-sublabel">Current: {theme === 'dark' ? 'Dark mode' : 'Light mode'}</div>
          </div>
          <button className={`toggle ${theme === 'light' ? 'on' : ''}`} onClick={onThemeToggle} title="Toggle theme" />
        </div>
      </div>

      <div className="settings-card">
        <h3>🤖 AI Model</h3>
        <div className="settings-row">
          <div>
            <div className="settings-label">LLM Backend</div>
            <div className="settings-sublabel">Ollama — llama3.1:8b (local)</div>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--success)' }}>● Online</span>
        </div>
        <div className="settings-row">
          <div>
            <div className="settings-label">Privacy</div>
            <div className="settings-sublabel">100% offline — no data leaves your machine</div>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--success)' }}>● Secure</span>
        </div>
      </div>

      <div className="settings-card">
        <h3>🎙️ Voice (Speech-to-Text)</h3>
        <div className="settings-row">
          <div>
            <div className="settings-label">faster-whisper STT</div>
            <div className="settings-sublabel">Local, offline voice transcription</div>
          </div>
          <span style={{ fontSize: '0.75rem', color: voiceStatus?.available ? 'var(--success)' : 'var(--danger)' }}>
            {voiceStatus === null ? '...' : voiceStatus.available ? '● Available' : '● Not installed'}
          </span>
        </div>
        {voiceStatus && !voiceStatus.available && (
          <div style={{ marginTop: 8, fontSize: '0.8rem', color: 'var(--text-2)', background: 'var(--bg-3)', borderRadius: 6, padding: '8px 12px' }}>
            Run: <code>pip install faster-whisper</code> then restart the API server.
          </div>
        )}
      </div>

      <div className="settings-card">
        <h3>🔐 Security</h3>
        <div className="settings-row">
          <div>
            <div className="settings-label">Approval System</div>
            <div className="settings-sublabel">All destructive actions require your confirmation</div>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--success)' }}>● Active</span>
        </div>
        <div className="settings-row">
          <div>
            <div className="settings-label">Protected Paths</div>
            <div className="settings-sublabel">System dirs, Program Files, User root</div>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--success)' }}>● Guarded</span>
        </div>
      </div>

      <div className="settings-card">
        <h3>ℹ️ About</h3>
        <div className="settings-row">
          <div className="settings-label">Version</div>
          <div className="settings-sublabel">OmniAgent v2.0.0</div>
        </div>
        <div className="settings-row">
          <div className="settings-label">API Endpoint</div>
          <div className="settings-sublabel">{API}</div>
        </div>
      </div>
    </div>
  );
}

// ─── PdfViewer ────────────────────────────────────────────────────────────────
function PdfViewer({ onOpenInChat }: { onOpenInChat: (text: string, explanation: string) => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [popup, setPopup] = useState<{ x: number; y: number; text: string; explanation: string; loading: boolean } | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [numPages, setNumPages] = useState(0);
  const [pdfDoc, setPdfDoc] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadedPath, setUploadedPath] = useState<string | null>(null);

  const renderPage = async (doc: any, pageNum: number) => {
    const page = await doc.getPage(pageNum);
    const viewport = page.getViewport({ scale: 1.4 });
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.height = viewport.height;
    canvas.width = viewport.width;
    await page.render({ canvasContext: canvas.getContext('2d')!, viewport }).promise;
  };

  useEffect(() => { if (pdfDoc) renderPage(pdfDoc, currentPage); }, [pdfDoc, currentPage]);
  
const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (!file) return;

  setUploading(true);

  try {
    // Step 1: Upload PDF to backend
    const form = new FormData();
    form.append("file", file);

    const uploadRes = await axios.post(
      `${API}/pdf/upload`,
      form,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );

    console.log("Upload response:", uploadRes.data);

    // Save uploaded path returned by backend
    setUploadedPath(uploadRes.data.filepath);

    // Step 2: Load PDF locally for viewing
    const { getDocument, GlobalWorkerOptions } = await import("pdfjs-dist");

    GlobalWorkerOptions.workerSrc = new URL(
      "pdfjs-dist/build/pdf.worker.min.mjs",
      import.meta.url
    ).toString();

    const arrayBuffer = await file.arrayBuffer();
    const doc = await getDocument({ data: arrayBuffer }).promise;

    setPdfDoc(doc);
    setNumPages(doc.numPages);
    setCurrentPage(1);
  } catch (err: any) {
    console.error("PDF upload/load error:", err);

    if (err.response) {
      alert(
        `Upload failed (${err.response.status}): ` +
        JSON.stringify(err.response.data)
      );
    } else {
      alert("Could not load PDF: " + err.message);
    }
  } finally {
    setUploading(false);

    // Optional: reset input so same file can be selected again
    e.target.value = "";
  }
};

  const handleMouseUp = async (e: React.MouseEvent) => {
    const selected = window.getSelection()?.toString().trim();
    if (!selected || selected.length < 10) return;
    setPopup({ x: e.clientX, y: e.clientY, text: selected, explanation: '', loading: true });
    try {
      const res = await axios.post(`${API}/pdf/explain`, { text: selected });
      setPopup(p => p ? { ...p, explanation: res.data.explanation, loading: false } : null);
    } catch {
      setPopup(p => p ? { ...p, explanation: 'Could not generate explanation.', loading: false } : null);
    }
  };

  return (
    <div className="pdf-page">
      <div className="pdf-toolbar">
        <label className="pdf-upload-btn">
          <input type="file" accept=".pdf" onChange={handleUpload} />
          {uploading ? '⏳ Loading...' : '📄 Open PDF'}
        </label>
        {numPages > 0 && (
          <>
            <button className="topbar-btn" onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}>←</button>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-2)' }}>Page {currentPage} / {numPages}</span>
            <button className="topbar-btn" onClick={() => setCurrentPage(p => Math.min(numPages, p + 1))} disabled={currentPage === numPages}>→</button>
          </>
        )}
        {uploadedPath && (
          <button className="topbar-btn" style={{marginLeft: 'auto', background: 'var(--accent)', color: 'white', border: 'none'}} 
                  onClick={() => onOpenInChat(`Analyze the document at path: ${uploadedPath}`, '')}>
            Chat about full PDF
          </button>
        )}
        {!pdfDoc && <span style={{ fontSize: '0.85rem', color: 'var(--text-2)' }}>Open a PDF, then select text for instant AI explanation</span>}
      </div>

      <div className="pdf-area" onMouseUp={handleMouseUp}>
        {pdfDoc ? (
          <div className="pdf-canvas-wrap">
            <canvas ref={canvasRef} style={{ display: 'block' }} />
          </div>
        ) : (
          <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-2)' }}>
            <FileText size={64} style={{ opacity: 0.3, marginBottom: 16 }} />
            <p>Open a PDF to start reading</p>
          </div>
        )}
      </div>

      {popup && (
        <div className="pdf-popup" style={{ left: Math.min(popup.x, window.innerWidth - 340), top: Math.min(popup.y + 10, window.innerHeight - 220) }}>
          <button className="pdf-popup-close" onClick={() => setPopup(null)}>✕</button>
          <div className="pdf-popup-title">💡 AI Explanation</div>
          <div className="pdf-popup-content">
            {popup.loading ? '⏳ Generating explanation...' : popup.explanation}
          </div>
          {!popup.loading && (
            <button className="pdf-popup-btn" onClick={() => { onOpenInChat(popup.text, popup.explanation); setPopup(null); }}>
              Open in Chat →
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState<Page>('chat');
  const [theme, setTheme] = useState<string>(() => localStorage.getItem('theme') || 'dark');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [alwaysOnTop, setAlwaysOnTop] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const userId = getUserId();
  const [compactMode, setCompactMode] = useState(false);
  const prevGeometryRef = useRef<{ width: number; height: number; x: number; y: number } | null>(null);

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Auto-scroll
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  // Floating Window Toggle
  const toggleAlwaysOnTop = async () => {
    try {
      const appWindow = getCurrentWindow();
      const newState = !alwaysOnTop;
      await appWindow.setAlwaysOnTop(newState);
      setAlwaysOnTop(newState);
    } catch (e) {
      console.warn("Tauri window API not available", e);
    }
  };

  const handleToggleCompact = async (compact: boolean) => {
    try {
      const appWindow = getCurrentWindow();
      if (compact) {
        // Save current geometry to restore later
        const size = await appWindow.innerSize();
        const factor = await appWindow.scaleFactor();
        const physicalPos = await appWindow.outerPosition();
        
        prevGeometryRef.current = {
          width: Math.round(size.width / factor),
          height: Math.round(size.height / factor),
          x: Math.round(physicalPos.x / factor),
          y: Math.round(physicalPos.y / factor)
        };
        
        // Dynamic backend resize (applies Win32 style transformations)
        await axios.post(`${API}/desktop/resize`, { compact: true });
        setCompactMode(true);
      } else {
        // Dynamic backend resize (restores normal geometry & normal native window decorations)
        await axios.post(`${API}/desktop/resize`, { compact: false });
        
        // Wait briefly for Win32 to restore styles before moving
        setTimeout(async () => {
          if (prevGeometryRef.current) {
            const { width, height, x, y } = prevGeometryRef.current;
            // Set size and position back to their original geometries
            await appWindow.setSize(new (await import('@tauri-apps/api/dpi')).LogicalSize(width, height));
            await appWindow.setPosition(new (await import('@tauri-apps/api/dpi')).LogicalPosition(x, y));
          }
          setCompactMode(false);
        }, 100);
      }
    } catch {
      // Win32 fallback resizing for Microsoft Edge App Mode
      try {
        await axios.post(`${API}/desktop/resize`, { compact });
        setCompactMode(compact);
      } catch (err) {
        console.warn("Resize failed", err);
      }
    }
  };

  // Load sessions
  const loadSessions = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/sessions/${userId}`);
      setSessions(r.data);
    } catch { /* api might not be up yet */ }
  }, [userId]);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  // Load session messages
  const loadSession = async (sid: string) => {
    setSessionId(sid);
    setPage('chat');
    try {
      const r = await axios.get(`${API}/sessions/${sid}/messages`);
      setMessages(r.data.map((m: any) => ({ ...m, approvalState: undefined })));
    } catch { setMessages([]); }
  };

  const deleteSession = async (sid: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await axios.delete(`${API}/sessions/${sid}`).catch(() => {});
    if (sid === sessionId) { setSessionId(null); setMessages([]); }
    setSessions(prev => prev.filter(s => s.id !== sid));
  };

  const sendMessage = async (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    setInput('');
    setLoading(true);

    const tempUser: Msg = { id: `tmp_${Date.now()}`, role: 'user', content: msg, created_at: new Date().toISOString() };
    setMessages(prev => [...prev, tempUser]);

    try {
      const r = await axios.post(`${API}/chat/`, { session_id: sessionId, message: msg, user_id: userId });
      const data = r.data as Msg & { session_id?: string };
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id);
        loadSessions();
      }
      setMessages(prev => [...prev, {
        ...data,
        approvalState: data.approval_request ? 'pending' : undefined,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        id: `err_${Date.now()}`, role: 'assistant', content: '❌ Could not reach OmniAgent API. Is the backend running?',
        created_at: new Date().toISOString(),
      }]);
    } finally { setLoading(false); }
  };

  const handleApproval = async (actionKey: string, approved: boolean) => {
    // Local Voice Input Approval Intercept
    if (actionKey.startsWith('voice_send_')) {
      setMessages(prev => prev.map(m =>
        m.approval_request?.action_key === actionKey
          ? { ...m, approvalState: approved ? 'approved' : 'denied' }
          : m
      ));
      
      const approvalMsg = messages.find(m => m.approval_request?.action_key === actionKey);
      if (!approvalMsg?.approval_request) return;
      
      if (approved) {
        sendMessage(approvalMsg.approval_request.original_message);
      }
      return;
    }

    // Standard Backend Approval
    setMessages(prev => prev.map(m =>
      m.approval_request?.action_key === actionKey
        ? { ...m, approvalState: approved ? 'approved' : 'denied' }
        : m
    ));

    // Find original message for re-run
    const approvalMsg = messages.find(m => m.approval_request?.action_key === actionKey);
    if (!approvalMsg?.approval_request) return;

    setLoading(true);
    try {
      const r = await axios.post(`${API}/approvals/decide`, {
        action_key: actionKey,
        session_id: approvalMsg.approval_request.session_id || sessionId,
        user_id: userId,
        original_message: approvalMsg.approval_request.original_message,
        approved,
      });
      setMessages(prev => [...prev, { ...r.data, approvalState: undefined }]);
    } catch {
      setMessages(prev => [...prev, {
        id: `err_${Date.now()}`, role: 'assistant',
        content: approved ? '❌ Error executing approved action.' : 'Action cancelled.',
        created_at: new Date().toISOString(),
      }]);
    } finally { setLoading(false); }
  };

  const openInChat = (text: string, explanation: string) => {
    setPage('chat');
    if (explanation) {
      setInput(`Regarding this PDF excerpt:\n\n"${text}"\n\nExplanation: ${explanation}\n\nCan you elaborate further?`);
    } else {
      setInput(text);
    }
    setTimeout(() => textareaRef.current?.focus(), 100);
  };

  const SUGGESTIONS = [
    'Play lo-fi music on YouTube 🎵',
    'Research the best AI papers 2024 📚',
    'Open VS Code 💻',
    'Explain this shell command: ls -la 🖥️',
  ];

  if (compactMode) {
    return (
      <div className="app compact-mode">
        <div className="main" data-tauri-drag-region>
          <div className="input-area" data-tauri-drag-region>
            <div className="input-wrap" data-tauri-drag-region>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => { setInput(e.target.value); }}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                placeholder={listening ? "Listening..." : "Message OmniAgent…"}
                rows={1}
              />
              <button 
                className={`icon-btn inline-control pin-btn ${alwaysOnTop ? 'active' : ''}`} 
                onClick={toggleAlwaysOnTop} 
                title="Toggle Always on Top"
                style={{ color: alwaysOnTop ? 'var(--accent)' : 'var(--text-3)', background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <Pin size={16} />
              </button>
              <button 
                className="icon-btn inline-control max-btn" 
                onClick={() => handleToggleCompact(false)} 
                title="Restore Full Window"
                style={{ color: 'var(--text-3)', background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <Maximize2 size={16} />
              </button>
              <VoiceButton 
                onTranscript={t => {
                  const cleaned = t.replace(/[^a-zA-Z0-9]/g, '').trim();
                  if (cleaned.length === 0) return;

                  setMessages(prev => [...prev, {
                    id: `voice_${Date.now()}`,
                    role: 'assistant',
                    content: `🎙️ **Voice Input Received:**\n> "${t}"\n\nShould I send this command?`,
                    created_at: new Date().toISOString(),
                    approval_request: {
                      action_key: `voice_send_${Date.now()}`,
                      session_id: sessionId || 'voice_input',
                      original_message: t
                    },
                    approvalState: 'pending'
                  }]);
                }} 
                disabled={loading} 
                isListening={setListening}
              />
              {loading ? (
                <div className="icon-btn send" style={{ opacity: 0.7, cursor: 'wait' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 'bold' }}>...</span>
                </div>
              ) : (
                <button className="icon-btn send" onClick={() => sendMessage()} disabled={!input.trim()}>
                  <Send size={16} />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      {/* ── Sidebar ── */}
      <div className={`sidebar ${sidebarOpen ? '' : 'collapsed'}`}>
        <div className="sidebar-logo">
          <BrainCircuit size={22} />
          OmniAgent
        </div>

        <button className="new-chat-btn" onClick={() => { setSessionId(null); setMessages([]); setPage('chat'); handleToggleCompact(false); }}>
          <PlusSquare size={16} /> New Chat
        </button>

        <div className="sidebar-nav">
          <button className={`sidebar-nav-item ${page === 'chat' ? 'active' : ''}`} onClick={() => setPage('chat')}>
            <MessageSquare size={16} /> Chat
          </button>
          <button className={`sidebar-nav-item ${page === 'pdf' ? 'active' : ''}`} onClick={() => setPage('pdf')}>
            <FileText size={16} /> PDF Explainer
          </button>
          <button className={`sidebar-nav-item ${page === 'memory' ? 'active' : ''}`} onClick={() => setPage('memory')}>
            <Database size={16} /> Memory
          </button>
          <button className={`sidebar-nav-item ${page === 'settings' ? 'active' : ''}`} onClick={() => setPage('settings')}>
            <Settings size={16} /> Settings
          </button>
        </div>

        <div className="sidebar-section-title">Recent Chats</div>
        <div className="history-list">
          {sessions.length === 0 && <div style={{ padding: '8px 10px', fontSize: '0.8rem', color: 'var(--text-3)' }}>No sessions yet</div>}
          {sessions.map(s => (
            <div key={s.id} className={`history-item ${s.id === sessionId ? 'active' : ''}`} onClick={() => loadSession(s.id)} title={s.title}>
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.title || 'Untitled Chat'}</span>
              <button className="history-item-delete" onClick={e => deleteSession(s.id, e)} title="Delete"><Trash2 size={12} /></button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Main ── */}
      <div className="main">
        {/* Topbar */}
        <div className="topbar">
          <button className="topbar-btn" onClick={() => setSidebarOpen(o => !o)} title="Toggle sidebar">
            <ChevronLeft size={16} style={{ transform: sidebarOpen ? '' : 'rotate(180deg)', transition: '0.2s' }} />
          </button>
          <span className="topbar-title">
            {page === 'chat' ? '💬 Chat' : page === 'pdf' ? '📄 PDF Explainer' : '⚙️ Settings'}
          </span>
          <button className={`topbar-btn ${alwaysOnTop ? 'active' : ''}`} onClick={toggleAlwaysOnTop} title="Toggle Always on Top (Floating Widget)" style={{ color: alwaysOnTop ? 'var(--accent)' : '' }}>
            <Pin size={16} />
          </button>
          <button className="topbar-btn minimize-maximize-btn" onClick={() => handleToggleCompact(true)} title="Minimize to Floating Search Bar">
            <Minimize2 size={16} />
          </button>
          <button className="topbar-btn" onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')} title="Toggle theme">
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>

        {/* Pages */}
        {page === 'settings' && <SettingsPage theme={theme} onThemeToggle={() => setTheme(t => t === 'dark' ? 'light' : 'dark')} />}
        {page === 'pdf' && <PdfViewer onOpenInChat={openInChat} />}
        {page === 'memory' && (
          <div className="settings-page" style={{textAlign: 'center', marginTop: '10vh'}}>
            <Database size={48} style={{color: 'var(--text-3)', marginBottom: 16}} />
            <h2>Agent Memory</h2>
            <p style={{color: 'var(--text-2)', marginTop: 8}}>Memory module is online. OmniAgent will learn your preferences over time.</p>
          </div>
        )}

        {page === 'chat' && (
          <>
            <div className="chat-area">
              {messages.length === 0 ? (
                <div className="chat-empty">
                  <div className="chat-empty-icon"><BrainCircuit size={32} color="white" /></div>
                  <h2>OmniAgent is ready</h2>
                  <p>Your fully offline AI copilot. Ask me anything — I can browse the web, play YouTube, manage files, run code, and more.</p>
                  <div className="suggestion-chips">
                    {SUGGESTIONS.map(s => (
                      <button key={s} className="chip" onClick={() => sendMessage(s)}>{s}</button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map(m => <MessageBubble key={m.id} msg={m} onDecide={handleApproval} />)
              )}
              {loading && (
                <div className="msg-row assistant">
                  <div className="msg-avatar">🤖</div>
                  <div className="msg-bubble">
                    <div className="typing-dots"><span/><span/><span/></div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            <div className="input-area">
              <div className="input-wrap">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={e => { setInput(e.target.value); e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px'; }}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                  placeholder={listening ? "Listening... Speak now." : "Message OmniAgent… (Shift+Enter for newline)"}
                  rows={1}
                />
                <VoiceButton 
                  onTranscript={t => {
                    const cleaned = t.replace(/[^a-zA-Z0-9]/g, '').trim();
                    if (cleaned.length === 0) return; // Ignore silent/hallucinated transcripts

                    setMessages(prev => [...prev, {
                      id: `voice_${Date.now()}`,
                      role: 'assistant',
                      content: `🎙️ **Voice Input Received:**\n> "${t}"\n\nShould I send this command?`,
                      created_at: new Date().toISOString(),
                      approval_request: {
                        action_key: `voice_send_${Date.now()}`,
                        session_id: sessionId || 'voice_input',
                        original_message: t
                      },
                      approvalState: 'pending'
                    }]);
                  }} 
                  disabled={loading} 
                  isListening={setListening}
                />
                <button className="icon-btn send" onClick={() => sendMessage()} disabled={!input.trim() || loading}>
                  <Send size={16} />
                </button>
              </div>
              <div className="input-hint">OmniAgent runs entirely offline · Your data never leaves your machine</div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
