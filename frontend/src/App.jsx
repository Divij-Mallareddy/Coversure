import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { ChatPanel } from './components/ChatPanel';
import { Navbar } from './components/Navbar';
import { UploadPanel } from './components/UploadPanel';

const API_BASE = 'http://127.0.0.1:8000';
const MAX_SELECTED_DOCS = 5;

function App() {
  const [mode, setMode] = useState('single');
  const [messages, setMessages] = useState([]);
  const [files, setFiles] = useState([]);
  const [knowledgeDocuments, setKnowledgeDocuments] = useState([]);
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [selectionMessage, setSelectionMessage] = useState('');
  const [uploadStatus, setUploadStatus] = useState('success');
  const [query, setQuery] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    const loadKnowledgeDocuments = async () => {
      try {
        const res = await axios.get(`${API_BASE}/knowledge/documents`);
        setKnowledgeDocuments(Array.isArray(res.data) ? res.data : []);
      } catch (err) {
        setKnowledgeDocuments([]);
      }
    };

    loadKnowledgeDocuments();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAsking]);

  const toggleKnowledgeDocument = (documentId) => {
    setSelectedDocs((currentDocs) => {
      if (currentDocs.includes(documentId)) {
        setSelectionMessage('');
        return currentDocs.filter((id) => id !== documentId);
      }

      if (currentDocs.length >= MAX_SELECTED_DOCS) {
        setSelectionMessage('Maximum 5 documents allowed');
        return currentDocs;
      }

      setSelectionMessage('');
      return [...currentDocs, documentId];
    });
  };

  const handleModeSwitch = async (newMode) => {
    setMode(newMode);
    setFiles([]);
    setMessages([]);
    setUploadStatus('success');
    try {
      await axios.post(`${API_BASE}/clear/`);
    } catch (e) {
      setUploadStatus('idle');
    }
  };

  const onFileDrop = (event) => {
    event.preventDefault();
    const droppedFiles = Array.from(event.dataTransfer.files).filter((file) => file.type === 'application/pdf');
    handleAddFiles(droppedFiles);
  };

  const onFileSelect = (event) => {
    const selected = Array.from(event.target.files);
    handleAddFiles(selected);
  };

  const handleAddFiles = (newFiles) => {
    if (newFiles.length === 0) return;

    if (mode === 'single') {
      setFiles([newFiles[0]]);
      setUploadStatus('idle');
    } else {
      setFiles((currentFiles) => [...currentFiles, ...newFiles].slice(0, 8));
      setUploadStatus('idle');
    }
  };

  const removeFile = (index) => {
    const remainingFiles = files.filter((_, i) => i !== index);
    setFiles(remainingFiles);
    setUploadStatus(remainingFiles.length > 0 ? 'idle' : 'success');
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploadStatus('uploading');
    
    try {
      if (mode === 'single') {
        const formData = new FormData();
        formData.append('file', files[0]);
        formData.append('append', false);
        await axios.post(`${API_BASE}/upload/`, formData);
      } else {
        await axios.post(`${API_BASE}/clear/`);
        for (let i = 0; i < files.length; i++) {
          const formData = new FormData();
          formData.append('file', files[i]);
          formData.append('append', true);
          await axios.post(`${API_BASE}/upload/`, formData);
        }
      }
      setUploadStatus('success');
      setMessages([{ role: 'ai', content: `Base initialized with ${files.length} document(s). I am ready to answer your questions.` }]);
    } catch (err) {
      setUploadStatus('error');
    }
  };

  const askQuestion = async (event) => {
    event?.preventDefault();
    if (!query.trim() || isAsking) return;

    if (uploadStatus !== 'success') {
      alert('Please upload and build the document base first.');
      return;
    }

    const currentQuery = query.trim();
    setQuery('');
    setMessages((currentMessages) => [...currentMessages, { role: 'user', content: currentQuery }]);
    setIsAsking(true);

    try {
      const res = await axios.post(`${API_BASE}/ask/`, {
        question: currentQuery,
        selected_docs: selectedDocs,
      });
      const answer = res.data.answer || res.data.error || 'No answer was returned.';
      const sources = Array.isArray(res.data.sources) ? [...new Set(res.data.sources)] : [];
      setMessages((currentMessages) => [...currentMessages, { role: 'ai', content: answer, sources }]);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const message = typeof detail === 'string' && detail.trim()
        ? `Backend error: ${detail}`
        : 'Sorry, I encountered an error answering your question.';
      setMessages((currentMessages) => [
        ...currentMessages,
        { role: 'ai', content: message },
      ]);
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-50 font-sans">
      <Navbar mode={mode} onModeSwitch={handleModeSwitch} />
      <main className="flex flex-1 overflow-hidden">
        <UploadPanel
          mode={mode}
          files={files}
          uploadStatus={uploadStatus}
          onFileDrop={onFileDrop}
          onFileSelect={onFileSelect}
          onRemoveFile={removeFile}
          onUpload={handleUpload}
          onRestart={() => setUploadStatus('idle')}
          knowledgeDocuments={knowledgeDocuments}
          selectedDocs={selectedDocs}
          selectionMessage={selectionMessage}
          onToggleDocument={toggleKnowledgeDocument}
        />
        <ChatPanel
          messages={messages}
          isAsking={isAsking}
          uploadStatus={uploadStatus}
          query={query}
          onQueryChange={setQuery}
          onAsk={askQuestion}
          chatEndRef={chatEndRef}
        />
      </main>
    </div>
  );
}

export default App;
