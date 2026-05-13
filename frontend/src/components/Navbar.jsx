import { Database, File } from 'lucide-react';
import { cn } from '../lib/cn';

export function Navbar({ mode, onModeSwitch }) {
  return (
    <nav className="flex items-center justify-between px-8 py-4 bg-white border-b border-slate-200">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
          <Database className="w-5 h-5 text-white" />
        </div>
        <h1 className="text-xl font-bold text-slate-800">Insurance RAG Assistant</h1>
      </div>

      <div className="flex bg-slate-100 p-1 rounded-xl">
        <button
          onClick={() => onModeSwitch('single')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
            mode === 'single' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-700',
          )}
        >
          <File className="w-4 h-4" />
          Single Policy
        </button>
        <button
          onClick={() => onModeSwitch('memory')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
            mode === 'memory' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-700',
          )}
        >
          <Database className="w-4 h-4" />
          Memory Base
        </button>
      </div>
    </nav>
  );
}
