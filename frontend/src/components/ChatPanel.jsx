import { MessageSquare, Send } from 'lucide-react';
import { cn } from '../lib/cn';

export function ChatPanel({
  messages,
  isAsking,
  uploadStatus,
  query,
  onQueryChange,
  onAsk,
  chatEndRef,
}) {
  const canAsk = uploadStatus === 'success' && !isAsking;

  return (
    <section className="flex-1 flex flex-col bg-slate-50/50 relative">
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
          <MessageSquare className="w-16 h-16 mb-4 opacity-20" />
          <p className="text-lg font-medium text-slate-500">How can I help you understand your policy?</p>
          <p className="text-sm">Ask from the backend knowledge base or add optional session documents.</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={cn('flex w-full', message.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              <div
                className={cn(
                  'max-w-[80%] p-4 rounded-2xl shadow-sm text-[15px] leading-relaxed',
                  message.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-tr-sm'
                    : 'bg-white text-slate-700 border border-slate-200 rounded-tl-sm',
                )}
              >
                {message.content}
                {message.role === 'ai' && Array.isArray(message.sources) && message.sources.length > 0 && (
                  <div className="mt-4 border-t border-slate-200 pt-3">
                    <p className="text-xs font-semibold text-slate-500">Sources used:</p>
                    <ul className="mt-1 space-y-1">
                      {message.sources.map((source) => (
                        <li key={source} className="text-xs text-slate-500">
                          • {source}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
          {isAsking && (
            <div className="flex justify-start w-full">
              <div className="bg-white text-slate-700 border border-slate-200 rounded-2xl rounded-tl-sm p-4 shadow-sm flex items-center gap-2">
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
      )}

      <div className="p-4 bg-white border-t border-slate-200">
        <form onSubmit={onAsk} className="max-w-3xl mx-auto relative flex items-center">
          <input
            type="text"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder={uploadStatus === 'success' ? 'Ask the knowledge base...' : 'Process selected documents to continue'}
            disabled={!canAsk}
            className="w-full pl-5 pr-14 py-4 rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!query.trim() || !canAsk}
            className="absolute right-2 p-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:hover:bg-indigo-600 transition-colors"
            aria-label="Send question"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
        <div className="text-center mt-2">
          <span className="text-xs text-slate-400">AI can make mistakes. Verify critical coverage details in your original document.</span>
        </div>
      </div>
    </section>
  );
}
