"use client";

import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Link from 'next/link';
import { BrainCircuit, UploadCloud, Send, Loader2, CheckCircle2, AlertTriangle, FileText, LayoutDashboard, Library, Download, ChevronDown, Zap, Terminal, Timer, Database, Activity, Cpu } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

type TelemetryData = {
  execution_time: number;
  cache_hits: number;
  api_calls: number;
  tokens_saved: number;
};

// NEW: Object-based log state for permanent timestamps
interface LogEntry {
  time: string;
  message: string;
}

export default function AgenticDashboard() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('single');
  const [isModeDropdownOpen, setIsModeDropdownOpen] = useState(false);
  const [report, setReport] = useState('');
  const [cleanTitle, setCleanTitle] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // NEW: Updated logs state and minimize toggle
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isLogsMinimized, setIsLogsMinimized] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  
  const [uploadStatus, setUploadStatus] = useState<{ type: 'idle' | 'loading' | 'success' | 'error', message: string }>({ type: 'idle', message: '' });
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logsEndRef.current && !isLogsMinimized) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isLogsMinimized]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsModeDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [dropdownRef]);

  const saveToHistory = (searchQuery: string, searchMode: string, finalReport: string) => {
    const existingHistory = JSON.parse(localStorage.getItem('agenticHistory') || '[]');
    const newEntry = {
      id: Date.now().toString(),
      query: searchQuery,
      mode: searchMode === 'single' ? 'Flash Agent' : 'Deep Parallel',
      report: finalReport,
      date: new Date().toLocaleString()
    };
    localStorage.setItem('agenticHistory', JSON.stringify([newEntry, ...existingHistory]));
  };

  const handleDownload = () => {
    const blob = new Blob([`# ${cleanTitle}\n\n${report}`], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${cleanTitle.replace(/\s+/g, '_').toLowerCase()}_report.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getTimeStamp = () => {
    return new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const handleResearch = async () => {
    if (!query.trim()) return;
    
    setIsLoading(true);
    setReport('');
    setTelemetry(null);
    setIsLogsMinimized(false); // Auto-expand logs on new search
    
    // Lock the starting timestamp
    setLogs([{ time: getTimeStamp(), message: "[System] Initializing Agentic AI Research Engine..." }]);
    setCleanTitle(query);
    
    try {
      const response = await fetch(`${API_URL}/research-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, mode })
      });
      
      if (!response.body) throw new Error("No readable stream available.");
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() || "";
        
        for (const block of blocks) {
          if (!block.trim()) continue;
          
          const eventMatch = block.match(/^event:\s*(.*)/m);
          const dataMatch = block.match(/^data:\s*(.*)/m);
          
          if (eventMatch && dataMatch) {
            const event = eventMatch[1].trim();
            const dataStr = dataMatch[1].trim();
            
            try {
              const data = JSON.parse(dataStr);
              
              if (event === 'progress') {
                // Lock timestamp instantly on arrival
                setLogs(prev => [...prev, { time: getTimeStamp(), message: data.message || data }]);
              } else if (event === 'telemetry') {
                setTelemetry(data);
              } else if (event === 'complete') {
                const cleanedReport = data.report.replace(/^(#\s*)?Research Summary:?\s*/i, '').trim();
                setReport(cleanedReport);
                saveToHistory(query, mode, cleanedReport);
              } else if (event === 'error') {
                setLogs(prev => [...prev, { time: getTimeStamp(), message: `[Fatal Error] ${data.message || data}` }]);
                setReport(`**Agentic Error:** ${data.message || data}`);
              }
            } catch (err) {
              console.error("Failed to parse SSE JSON:", err);
            }
          }
        }
      }
    } catch (error) {
      setReport(`**Connection Error:** Make sure the FastAPI backend is running and the streaming endpoint is accessible.`);
    } finally {
      setIsLoading(false);
      setQuery(''); 
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadStatus({ type: 'loading', message: `Ingesting ${file.name}...` });
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_URL}/upload-pdf`, {
        method: 'POST',
        body: formData
      });
      const data = await response.json();

      if (response.ok) {
        setUploadStatus({ type: 'success', message: `${file.name} embedded successfully!` });
      } else {
        setUploadStatus({ type: 'error', message: data.detail || 'Upload failed.' });
      }
    } catch (error) {
      setUploadStatus({ type: 'error', message: 'Connection error during upload.' });
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 font-sans overflow-hidden">
      
      {/* SIDEBAR */}
      <aside className="w-80 bg-slate-900 border-r border-slate-800 p-6 flex flex-col relative z-20">
        <div className="flex items-center gap-3 mb-10">
          <BrainCircuit className="w-8 h-8 text-blue-500" />
          <h1 className="text-2xl font-bold text-white tracking-tight">Research Assistant</h1>
        </div>

        <div className="mb-10 flex flex-col gap-2">
          <h2 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Menu</h2>
          <Link href="/" className="flex items-center gap-3 px-4 py-3 bg-blue-600/10 text-blue-400 rounded-xl font-medium border border-blue-500/20 transition-colors">
            <LayoutDashboard className="w-5 h-5" />
            New Research
          </Link>
          <Link href="/history" className="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl font-medium transition-colors">
            <Library className="w-5 h-5" />
            Research Library
          </Link>
        </div>

        <div className="mt-auto mb-6">
          <h2 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Knowledge Base</h2>
          <label className="cursor-pointer flex flex-col items-center justify-center w-full h-36 border-2 border-slate-700 border-dashed rounded-xl hover:bg-slate-800 hover:border-blue-500 transition-all duration-200 group">
            <UploadCloud className="w-8 h-8 text-slate-500 group-hover:text-blue-400 mb-2 transition-colors" />
            <p className="text-sm font-medium text-slate-300">Upload PDF to RAG</p>
            <p className="text-xs text-slate-500 mt-1">Updates local Vector DB</p>
            <input type="file" className="hidden" accept=".pdf" onChange={handleFileUpload} />
          </label>
          {uploadStatus.type !== 'idle' && (
            <div className={`mt-4 p-3 rounded-lg flex items-start gap-2 text-sm ${uploadStatus.type === 'loading' ? 'bg-blue-900/20 text-blue-400 border border-blue-900/50' : uploadStatus.type === 'success' ? 'bg-emerald-900/20 text-emerald-400 border border-emerald-900/50' : 'bg-red-900/20 text-red-400 border border-red-900/50'}`}>
              {uploadStatus.type === 'loading' && <Loader2 className="w-4 h-4 animate-spin mt-0.5" />}
              {uploadStatus.type === 'success' && <CheckCircle2 className="w-4 h-4 mt-0.5" />}
              {uploadStatus.type === 'error' && <AlertTriangle className="w-4 h-4 mt-0.5" />}
              <span className="leading-tight">{uploadStatus.message}</span>
            </div>
          )}
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 flex flex-col h-full relative">
        <div className="flex-1 overflow-y-auto p-10 pb-40 relative z-10">
          <div className="max-w-4xl mx-auto">
            
            {!report && !isLoading && logs.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full mt-32 text-center animate-in fade-in duration-500">
                <FileText className="w-16 h-16 text-slate-800 mb-6" />
                <h2 className="text-3xl font-bold text-white mb-2">Initialize Research</h2>
                <p className="text-slate-400 max-w-md">Enter a topic below. The agent will autonomously navigate the web, compile data, and synthesize a cited report.</p>
              </div>
            )}

            {/* NEW: Collapsible Terminal - Renders if logs exist, regardless of loading state */}
            {logs.length > 0 && (
              <div className="mt-8 mb-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                {isLoading && (
                  <div className="flex items-center gap-3 mb-4">
                    <div className="relative">
                      <div className="absolute inset-0 bg-blue-500 blur-md opacity-40 rounded-full"></div>
                      <Loader2 className="w-6 h-6 text-blue-400 animate-spin relative z-10" />
                    </div>
                    <h3 className="text-xl font-bold text-white tracking-tight">Agentic Workflow Active</h3>
                  </div>
                )}
                
                <div className="bg-slate-950 border border-slate-800 rounded-xl shadow-2xl transition-all duration-300">
                  <div className="bg-slate-900 border-b border-slate-800 px-4 py-3 flex items-center justify-between rounded-t-xl">
                    <div className="flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-slate-500" />
                      <span className="text-xs font-mono text-slate-400">langgraph-orchestrator.log</span>
                      {isLoading && <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse ml-2" />}
                    </div>
                    <button 
                      onClick={() => setIsLogsMinimized(!isLogsMinimized)}
                      className="text-slate-500 hover:text-white text-xs px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 transition"
                    >
                      {isLogsMinimized ? "Expand Logs" : "Minimize Logs"}
                    </button>
                  </div>
                  
                  {!isLogsMinimized && (
                    <div className="p-6 h-72 overflow-y-auto font-mono text-xs md:text-sm flex flex-col gap-2 rounded-b-xl">
                      {logs.map((log, index) => (
                        <div 
                          key={index} 
                          className={`animate-in fade-in duration-300 ${log.message.includes('[Fatal Error]') ? 'text-red-400' : log.message.includes('Cache hit') ? 'text-emerald-400' : 'text-blue-300'}`}
                        >
                          <span className="text-slate-600 mr-3">[{log.time}]</span>
                          {log.message}
                        </div>
                      ))}
                      <div ref={logsEndRef} />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* VERCEL-STYLE TELEMETRY DASHBOARD */}
            {telemetry && report && !isLoading && (
              <div className="mb-8 grid grid-cols-4 gap-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center gap-4">
                  <div className="p-3 bg-blue-900/20 text-blue-400 rounded-lg">
                    <Timer className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-0.5">Execution Time</div>
                    <div className="text-xl font-semibold text-white">{telemetry.execution_time}s</div>
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center gap-4">
                  <div className="p-3 bg-indigo-900/20 text-indigo-400 rounded-lg">
                    <Activity className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-0.5">API Calls</div>
                    <div className="text-xl font-semibold text-white">{telemetry.api_calls}</div>
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center gap-4">
                  <div className="p-3 bg-emerald-900/20 text-emerald-400 rounded-lg">
                    <Database className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-0.5">Cache Hits</div>
                    <div className="text-xl font-semibold text-white">{telemetry.cache_hits}</div>
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center gap-4">
                  <div className="p-3 bg-amber-900/20 text-amber-400 rounded-lg">
                    <Cpu className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-0.5">Tokens Saved</div>
                    <div className="text-xl font-semibold text-white">~{telemetry.tokens_saved.toLocaleString()}</div>
                  </div>
                </div>
              </div>
            )}

            {/* FINAL REPORT */}
            {report && !isLoading && (
              <div className="bg-slate-900 p-10 rounded-2xl border border-slate-800 shadow-xl animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="flex items-start justify-between border-b border-slate-800 pb-6 mb-6">
                  <div>
                    <span className="text-xs font-bold text-blue-500 uppercase tracking-widest mb-2 block">Final Report</span>
                    <h2 className="text-3xl font-bold text-white capitalize leading-snug">{cleanTitle}</h2>
                  </div>
                  <button 
                    onClick={handleDownload}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition-colors border border-slate-700 hover:border-slate-600"
                  >
                    <Download className="w-4 h-4" />
                    <span className="text-sm font-medium">Download</span>
                  </button>
                </div>
                <div className="prose prose-invert prose-blue max-w-none prose-headings:text-slate-200 prose-a:text-blue-400 hover:prose-a:text-blue-300">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* INPUT DOCK */}
        <div className="absolute bottom-0 w-full bg-gradient-to-t from-slate-950 via-slate-950 to-transparent pt-12 pb-8 px-10 z-20">
          <div className="max-w-4xl mx-auto bg-slate-900 border border-slate-700 rounded-2xl p-4 shadow-2xl flex flex-col gap-3 transition-all focus-within:border-blue-500/50 focus-within:shadow-blue-900/20">
            
            <div className="flex px-2">
              <input 
                type="text" 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleResearch()}
                placeholder="What would you like to research today?" 
                className="flex-1 bg-transparent border-none text-white text-lg focus:ring-0 outline-none placeholder-slate-500"
                disabled={isLoading}
              />
            </div>
            
            <div className="flex items-center justify-between border-t border-slate-800 pt-3 mt-1 px-2 relative">
              
              <div className="relative" ref={dropdownRef}>
                <button 
                  onClick={() => setIsModeDropdownOpen(!isModeDropdownOpen)}
                  disabled={isLoading}
                  className="flex items-center gap-2 px-3 py-2 bg-slate-950 hover:bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors disabled:opacity-50"
                >
                  {mode === 'single' ? (
                    <><Zap className="w-4 h-4 text-amber-400"/> Flash Agent</>
                  ) : (
                    <><BrainCircuit className="w-4 h-4 text-purple-400"/> Deep Parallel</>
                  )}
                  <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform ${isModeDropdownOpen ? 'rotate-180' : ''}`} />
                </button>

                {isModeDropdownOpen && (
                  <div className="absolute bottom-full left-0 mb-2 w-64 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl overflow-hidden z-50 animate-in fade-in slide-in-from-bottom-2 duration-200">
                    <button 
                      onClick={() => { setMode('single'); setIsModeDropdownOpen(false); }} 
                      className={`w-full text-left px-4 py-3 hover:bg-slate-700 flex items-start gap-3 transition-colors border-b border-slate-700 ${mode === 'single' ? 'bg-slate-700/50' : ''}`}
                    >
                      <Zap className="w-5 h-5 text-amber-400 mt-0.5" />
                      <div>
                        <div className="text-sm font-semibold text-white">Flash Agent</div>
                        <div className="text-xs text-slate-400 mt-0.5">Iterative loop. Fast & efficient.</div>
                      </div>
                    </button>
                    <button 
                      onClick={() => { setMode('deep'); setIsModeDropdownOpen(false); }} 
                      className={`w-full text-left px-4 py-3 hover:bg-slate-700 flex items-start gap-3 transition-colors ${mode === 'deep' ? 'bg-slate-700/50' : ''}`}
                    >
                      <BrainCircuit className="w-5 h-5 text-purple-400 mt-0.5" />
                      <div>
                        <div className="text-sm font-semibold text-white">Deep Parallel</div>
                        <div className="text-xs text-slate-400 mt-0.5">Multi-agent architecture. Highly detailed.</div>
                      </div>
                    </button>
                  </div>
                )}
              </div>

              <button 
                onClick={handleResearch} 
                disabled={isLoading || !query.trim()} 
                className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-semibold rounded-xl px-6 py-2 transition-all flex items-center gap-2"
              >
                {isLoading ? 'Processing...' : 'Research'}
                {!isLoading && <Send className="w-4 h-4" />}
              </button>
            </div>

          </div>
        </div>
      </main>
    </div>
  );
}