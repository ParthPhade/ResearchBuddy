import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import mermaid from 'mermaid';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import './App.css';
import { GoogleLogin, googleLogout, CredentialResponse } from '@react-oauth/google';

// Initializing mermaid
const initMermaid = (isDark: boolean) => {
  mermaid.initialize({
    startOnLoad: true,
    theme: isDark ? 'dark' : 'base',
    themeVariables: {
      primaryColor: '#6366f1',
      primaryTextColor: '#fff',
      lineColor: '#6366f1',
      secondaryColor: '#f1f5f9',
    }
  });
};

const MermaidChart = ({ chart }: { chart: string }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current && chart) {
      mermaid.render(`mermaid-${Math.random().toString(36).substr(2, 9)}`, chart).then((res) => {
        if (ref.current) ref.current.innerHTML = res.svg;
      }).catch((err) => {
        console.error("Mermaid Render Error:", err);
      });
    }
  }, [chart]);

  return <div ref={ref} className="mermaid-container" />;
};

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<string>('');
  const [fullText, setFullText] = useState<string>('');
  const [images, setImages] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [currentQuote, setCurrentQuote] = useState<string>('');
  const [error, setError] = useState<string>('');
  
  // Chat state
  const [chatInput, setChatInput] = useState<string>('');
  const [chatHistory, setChatHistory] = useState<{role: 'user' | 'ai', content: string}[]>([]);
  const [chatLoading, setChatLoading] = useState<boolean>(false);

  // Theme state
  const [theme, setTheme] = useState<string>(localStorage.getItem('theme') || 'light');
  
  // Auth state
  const [userToken, setUserToken] = useState<string | null>(localStorage.getItem('userToken'));
  
  // Settings state
  const [provider, setProvider] = useState<string>(localStorage.getItem('provider') || 'gemini');
  const [style, setStyle] = useState<string>(localStorage.getItem('style') || 'simple');
  const [apiKey, setApiKey] = useState<string>(localStorage.getItem('apiKey') || '');
  const [showSettings, setShowSettings] = useState<boolean>(false);

  const quotes = [
    "Science is the poetry of reality. — Richard Dawkins",
    "The important thing is not to stop questioning. — Albert Einstein",
    "Data is the new oil. It's valuable, but if unrefined it cannot really be used. — Clive Humby",
    "The best way to predict the future is to create it. — Peter Drucker",
    "Innovation distinguishes between a leader and a follower. — Steve Jobs",
    "Everything is theoretically impossible, until it is done. — Robert A. Heinlein",
    "The art and science of asking questions is the source of all knowledge. — Thomas Berger",
    "Research is what I'm doing when I don't know what I'm doing. — Wernher von Braun"
  ];

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    initMermaid(theme === 'dark');
  }, [theme]);

  useEffect(() => {
    let quoteInterval: any;
    if (loading) {
      setCurrentQuote(quotes[Math.floor(Math.random() * quotes.length)]);
      quoteInterval = setInterval(() => {
        setCurrentQuote(quotes[Math.floor(Math.random() * quotes.length)]);
      }, 3000);
    }
    return () => clearInterval(quoteInterval);
  }, [loading]);

  useEffect(() => {
    localStorage.setItem('provider', provider);
    localStorage.setItem('style', style);
    localStorage.setItem('apiKey', apiKey);
    if (userToken) localStorage.setItem('userToken', userToken);
    else localStorage.removeItem('userToken');
  }, [provider, style, apiKey, userToken]);

  const handleLoginSuccess = (response: CredentialResponse) => {
    if (response.credential) {
      setUserToken(response.credential);
      setError('');
    }
  };

  const handleLogout = () => {
    googleLogout();
    setUserToken(null);
    setAnalysis('');
    setImages([]);
    setFullText('');
    setChatHistory([]);
    setProgress(0);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a PDF file first.');
      return;
    }

    setLoading(true);
    setProgress(0);
    setError('');

    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 95) {
          clearInterval(progressInterval);
          return 95;
        }
        return prev + Math.random() * 15;
      });
    }, 1000);

    const formData = new FormData();
    formData.append('file', file);

    const headers: any = { 'Content-Type': 'multipart/form-data' };
    if (apiKey) headers['x-api-key'] = apiKey;
    else if (userToken) headers['Authorization'] = `Bearer ${userToken}`;
    else {
      clearInterval(progressInterval);
      setLoading(false);
      setError('Please sign in with Google or provide an API key in Settings.');
      return;
    }

    try {
      const response = await axios.post(`http://localhost:8000/analyze?provider=${provider}&style=${style}`, formData, { headers });
      setAnalysis(response.data.analysis);
      setImages(response.data.images || []);
      setFullText(response.data.full_text || '');
      setProgress(100);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An error occurred during analysis.');
    } finally {
      clearInterval(progressInterval);
      setLoading(false);
    }
  };

  const handleChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;

    const userMsg = chatInput;
    setChatInput('');
    setChatHistory(prev => [...prev, { role: 'user', content: userMsg }]);
    setChatLoading(true);

    const headers: any = {};
    if (apiKey) headers['x-api-key'] = apiKey;
    else if (userToken) headers['Authorization'] = `Bearer ${userToken}`;

    try {
      const response = await axios.post(`http://localhost:8000/chat?provider=${provider}`, null, {
        params: { question: userMsg, context: fullText },
        headers
      });
      setChatHistory(prev => [...prev, { role: 'ai', content: response.data.answer }]);
    } catch (err) {
      setChatHistory(prev => [...prev, { role: 'ai', content: "Sorry, I couldn't process that question." }]);
    } finally {
      setChatLoading(false);
    }
  };

  const exportPDF = async () => {
    const element = document.getElementById('report-to-export');
    if (!element) return;
    
    // Temporarily hide elements that shouldn't be in PDF (like the button itself)
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    
    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      backgroundColor: theme === 'dark' ? '#0f172a' : '#f8fafc',
      logging: false,
    });

    const imgData = canvas.toDataURL('image/png');
    const imgWidth = pageWidth;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    
    let heightLeft = imgHeight;
    let position = 0;

    // First page
    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;

    // Additional pages
    while (heightLeft >= 0) {
      position = heightLeft - imgHeight;
      pdf.addPage();
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;
    }

    pdf.save(`ResearchBuddy_Study_Guide_${Date.now()}.pdf`);
  };

  const renderMarkdown = (content: string) => {
    return (
      <ReactMarkdown
        components={{
          code({ node, inline, className, children, ...props }: any) {
            const chartContent = String(children).replace(/\n$/, '');
            const isMermaid = /language-mermaid/.test(className || '') || 
                             (!inline && (chartContent.startsWith('graph ') || chartContent.startsWith('sequenceDiagram')));
            
            if (isMermaid) {
              return <MermaidChart chart={chartContent} />;
            }

            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    );
  };

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1>ResearchBuddy <span className="badge">AI 2.5</span></h1>
          <div className="header-actions">
            <button className="btn-icon" onClick={toggleTheme} title="Toggle Theme">
              {theme === 'light' ? '🌙' : '☀️'}
            </button>
            {!userToken ? (
              <GoogleLogin onSuccess={handleLoginSuccess} theme="filled_blue" shape="pill" />
            ) : (
              <button className="logout-btn" onClick={handleLogout}>Logout</button>
            )}
            <button className="btn-icon" onClick={() => setShowSettings(!showSettings)} title="Settings">
              ⚙️
            </button>
          </div>
        </div>
        <p className="subtitle">Transforming complex papers into clear, visual insights.</p>
      </header>

      {showSettings && (
        <section className="settings-panel animate-in">
          <h3>Configuration</h3>
          <div className="setting-item">
            <label>AI Model Engine</label>
            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
              <option value="gemini">Google Gemini 2.5 (Fastest)</option>
              <option value="openai">OpenAI GPT-4o Mini</option>
            </select>
          </div>
          <div className="setting-item">
            <label>Analysis Style</label>
            <select value={style} onChange={(e) => setStyle(e.target.value)}>
              <option value="simple">Simple Guide (Analogy Based)</option>
              <option value="notebook">Notebook Style (Detailed Story)</option>
            </select>
          </div>
          <div className="setting-item">
            <label>Your Personal API Key (Optional)</label>
            <input 
              type="password" 
              placeholder="Paste your key here to skip login" 
              value={apiKey} 
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>
        </section>
      )}

      <main className="main-content">
        <div className="upload-card">
          <form onSubmit={handleSubmit} className="upload-section">
            <div className="file-drop">
              <input type="file" accept="application/pdf" onChange={handleFileChange} />
              <p style={{fontSize: '1.2rem', fontWeight: 600}}>
                {file ? file.name : "Click to select or drag your research paper (PDF)"}
              </p>
              <p style={{color: 'var(--text-dim)', marginTop: '0.5rem'}}>Unlock deep insights in seconds</p>
            </div>
            <button type="submit" disabled={loading} className="submit-btn primary">
              {loading ? `Analyzing... ${Math.round(progress)}%` : "Generate Study Guide"}
            </button>
          </form>
          {loading && (
            <>
              <div className="quote-container animate-in">
                <p className="quote-text">{currentQuote}</p>
              </div>
              <div className="progress-container">
                <div className="progress-bar" style={{ width: `${progress}%` }}></div>
              </div>
            </>
          )}
          {error && <div className="error-msg">{error}</div>}
        </div>

        {(analysis || images.length > 0) && (
          <div className="report-container animate-in">
            <div className="report-main">
              <button className="export-btn" onClick={exportPDF}>
                📄 Download as PDF
              </button>
              <div id="report-to-export">
                <div className="markdown-body">
                  {renderMarkdown(analysis || "")}
                </div>
              </div>

              <div className="chat-section">
                <h3>💬 Deep Dive Q&A</h3>
                <div className="chat-history">
                  {chatHistory.map((msg, i) => (
                    <div key={i} className={`chat-bubble ${msg.role}`}>
                      {msg.content}
                    </div>
                  ))}
                  {chatLoading && <div className="chat-bubble ai">Thinking...</div>}
                </div>
                <form onSubmit={handleChat} className="chat-input-group">
                  <input 
                    className="chat-input" 
                    placeholder="Ask a question about this paper..." 
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                  />
                  <button type="submit" className="chat-btn">Ask AI</button>
                </form>
              </div>
            </div>
            {images.length > 0 && (
              <aside className="report-sidebar">
                <h3>Visual Evidence</h3>
                <div className="image-grid">
                  {images.map((url, idx) => (
                    <div key={idx} className={`extracted-img-container`}>
                      <img src={url} alt={`Figure ${idx + 1}`} onClick={() => window.open(url)} />
                      <span style={{fontSize: '0.8rem', color: 'var(--text-dim)', textAlign: 'center', display: 'block', marginTop: '0.5rem'}}>
                        Figure {idx + 1}
                      </span>
                    </div>
                  ))}
                </div>
              </aside>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
