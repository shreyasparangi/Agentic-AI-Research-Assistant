"use client";

import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Link from 'next/link';
import { BrainCircuit, LayoutDashboard, Library, Clock, Database, X, Trash2 } from 'lucide-react';

interface HistoryItem {
  id: string;
  query: string;
  mode: string;
  report: string;
  date: string;
}

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedReport, setSelectedReport] = useState<HistoryItem | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      const saved = localStorage.getItem('agenticHistory');
      if (saved) {
        setHistory(JSON.parse(saved));
      }
    }, 0);

    return () => clearTimeout(timer);
  }, []);

  const clearHistory = () => {
    if(confirm("Are you sure you want to clear your research history?")) {
      localStorage.removeItem('agenticHistory');
      setHistory([]);
    }
  }

  // NEW: Individual delete function
  const deleteHistoryItem = (e: React.MouseEvent, idToDelete: string) => {
    e.stopPropagation(); // Prevents the card click event from opening the modal
    if(confirm("Delete this report from your archive?")) {
      const updatedHistory = history.filter(item => item.id !== idToDelete);
      setHistory(updatedHistory);
      localStorage.setItem('agenticHistory', JSON.stringify(updatedHistory));
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
          <Link href="/" className="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl font-medium transition-colors">
            <LayoutDashboard className="w-5 h-5" />
            New Research
          </Link>
          <Link href="/history" className="flex items-center gap-3 px-4 py-3 bg-blue-600/10 text-blue-400 rounded-xl font-medium border border-blue-500/20 transition-colors">
            <Library className="w-5 h-5" />
            Research Library
          </Link>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 overflow-y-auto p-10 relative">
        <div className="max-w-6xl mx-auto">
          
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-3xl font-bold text-white">Research Library</h2>
              <p className="text-slate-400 mt-1">Your localized archive of AI-generated reports.</p>
            </div>
            {history.length > 0 && (
              <button onClick={clearHistory} className="px-4 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-400/10 rounded-lg transition-colors border border-red-900/30">
                Clear Archive
              </button>
            )}
          </div>

          {/* EMPTY STATE */}
          {history.length === 0 && (
            <div className="text-center mt-32 border-2 border-dashed border-slate-800 rounded-2xl p-12 bg-slate-900/50">
              <Database className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-slate-300">No records found</h3>
              <p className="text-slate-500 mt-2">Run a research query on the dashboard to populate your library.</p>
            </div>
          )}

          {/* HISTORY GRID */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {history.map((item) => (
              <div 
                key={item.id} 
                onClick={() => setSelectedReport(item)}
                className="bg-slate-900 border border-slate-800 p-6 rounded-2xl cursor-pointer hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-900/20 transition-all group relative"
              >
                <div className="flex items-center gap-2 text-xs text-slate-500 mb-3">
                  <Clock className="w-3 h-3" />
                  <span>{item.date}</span>
                  <span className="ml-auto px-3 py-1 bg-slate-800 text-slate-300 rounded-full font-medium whitespace-nowrap flex items-center justify-center">
                    {item.mode}
                  </span>
                  
                  {/* NEW: Delete Button */}
                  <button 
                    onClick={(e) => deleteHistoryItem(e, item.id)}
                    className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-md transition-colors ml-1"
                    title="Delete report"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <h3 className="text-lg font-bold text-slate-200 group-hover:text-blue-400 transition-colors line-clamp-2">
                  {item.query}
                </h3>
                <p className="text-sm text-slate-500 mt-3 line-clamp-3">
                  {item.report.replace(/[#*]/g, '')}
                </p>
              </div>
            ))}
          </div>

        </div>
      </main>

      {/* REPORT VIEW MODAL */}
      {selectedReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-10 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 w-full max-w-4xl max-h-full rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            
            <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-900/50">
              <div>
                <h3 className="text-xl font-bold text-white line-clamp-1">{selectedReport.query}</h3>
                <p className="text-sm text-slate-500 mt-1">Archived on {selectedReport.date}</p>
              </div>
              <button 
                onClick={() => setSelectedReport(null)}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-full transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-8 overflow-y-auto">
              <div className="prose prose-invert prose-blue max-w-none prose-headings:border-b prose-headings:border-slate-800 prose-headings:pb-2 prose-a:text-blue-400">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {selectedReport.report}
                </ReactMarkdown>
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}