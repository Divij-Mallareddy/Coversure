import { FileText } from 'lucide-react';
import { cn } from '../lib/cn';

const MAX_DOCUMENTS = 5;

export function KnowledgeDocuments({
  documents,
  selectedDocs,
  selectionMessage,
  onToggleDocument,
}) {
  return (
    <section className="mt-6 border-t border-slate-200 pt-5">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Knowledge Documents</h3>
          <p className="text-xs text-slate-500">Select up to {MAX_DOCUMENTS} documents</p>
        </div>
        <span className="text-xs font-medium text-slate-500">
          {selectedDocs.length}/{MAX_DOCUMENTS}
        </span>
      </div>

      {documents.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-xs text-slate-500">
          No indexed knowledge documents found.
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {documents.map((document) => {
            const isSelected = selectedDocs.includes(document.id);
            const isDisabled = !isSelected && selectedDocs.length >= MAX_DOCUMENTS;

            return (
              <button
                key={document.id}
                type="button"
                onClick={() => onToggleDocument(document.id)}
                aria-disabled={isDisabled}
                title={document.id}
                className={cn(
                  'inline-flex max-w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs font-medium transition',
                  isSelected
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700 shadow-sm'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-indigo-200 hover:bg-slate-50',
                  isDisabled && 'cursor-not-allowed opacity-50 hover:border-slate-200 hover:bg-white',
                )}
              >
                <FileText className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{document.title || document.id}</span>
              </button>
            );
          })}
        </div>
      )}

      {selectionMessage && (
        <p className="mt-2 text-xs font-medium text-amber-600">{selectionMessage}</p>
      )}
    </section>
  );
}
