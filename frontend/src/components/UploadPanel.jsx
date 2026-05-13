import { CheckCircle, File, Loader2, RefreshCw, UploadCloud, X } from 'lucide-react';

export function UploadPanel({
  mode,
  files,
  uploadStatus,
  onFileDrop,
  onFileSelect,
  onRemoveFile,
  onUpload,
  onRestart,
}) {
  const isSingleMode = mode === 'single';

  return (
    <aside className="w-1/3 bg-white border-r border-slate-200 p-6 flex flex-col h-full overflow-y-auto">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-1">
          {isSingleMode ? 'Policy Upload' : 'Memory Base (Multi-Policy)'}
        </h2>
        <p className="text-sm text-slate-500">
          {isSingleMode
            ? 'Optional: upload one session policy PDF to add user-specific context.'
            : 'Optional: upload up to 8 session policies to compare with the backend knowledge base.'}
        </p>
      </div>

      <label
        onDragOver={(event) => event.preventDefault()}
        onDrop={onFileDrop}
        className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-slate-300 rounded-2xl bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer"
      >
        <UploadCloud className="w-10 h-10 text-slate-400 mb-3" />
        <p className="text-sm font-medium text-slate-700">Click or drag PDF files here</p>
        <p className="text-xs text-slate-500 mt-1">Backend knowledge works without upload</p>
        <input
          type="file"
          accept=".pdf"
          multiple={!isSingleMode}
          onChange={onFileSelect}
          className="hidden"
        />
      </label>

      {files.length > 0 && (
        <div className="mt-6 flex flex-col gap-2 flex-1">
          <h3 className="text-sm font-semibold text-slate-700">Selected Files ({files.length})</h3>
          <div className="flex flex-col gap-2 mb-4">
            {files.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg"
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  <File className="w-5 h-5 text-indigo-500 shrink-0" />
                  <span className="text-sm text-slate-700 truncate">{file.name}</span>
                </div>
                {uploadStatus !== 'uploading' && uploadStatus !== 'success' && (
                  <button
                    onClick={() => onRemoveFile(index)}
                    className="text-slate-400 hover:text-red-500 p-1"
                    aria-label={`Remove ${file.name}`}
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>

          {uploadStatus !== 'success' && (
            <button
              onClick={onUpload}
              disabled={uploadStatus === 'uploading'}
              className="mt-auto w-full py-3 bg-indigo-600 text-white rounded-xl font-medium shadow-sm hover:bg-indigo-700 transition flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {uploadStatus === 'uploading' ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Processing...
                </>
              ) : (
                isSingleMode ? 'Process Document' : 'Build Memory Base'
              )}
            </button>
          )}

          {uploadStatus === 'success' && (
            <div className="mt-auto p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3 text-emerald-700">
              <CheckCircle className="w-5 h-5" />
              <span className="text-sm font-medium">Ready for questions!</span>
              <button
                onClick={onRestart}
                className="ml-auto text-emerald-600 hover:text-emerald-800"
                title="Restart"
                aria-label="Restart upload"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
