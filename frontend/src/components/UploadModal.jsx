import { useState, useRef } from 'react';
import { api } from '../api';

/**
 * Z-AUDIT — Upload Modal
 * Two tabs: Single upload (audio + JSON) and Batch upload (Excel/CSV).
 */
export default function UploadModal({ onClose, onComplete, selectedModel, models }) {
  const [activeTab, setActiveTab] = useState('single');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Single upload state
  const [audioFile, setAudioFile] = useState(null);
  const [jsonText, setJsonText] = useState('');
  const audioRef = useRef(null);

  // Batch upload state
  const [batchFile, setBatchFile] = useState(null);
  const batchRef = useRef(null);

  // Model selection
  const [model, setModel] = useState(selectedModel || '');

  const handleSingleUpload = async () => {
    if (!jsonText.trim()) {
      setError('Please paste JSON metadata');
      return;
    }

    try {
      JSON.parse(jsonText);
    } catch {
      setError('Invalid JSON format. Please check the metadata.');
      return;
    }

    setUploading(true);
    setProgress(10);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('metadata', jsonText);
      formData.append('model', model);
      if (audioFile) {
        formData.append('audio_file', audioFile);
      }

      setProgress(30);
      const res = await api.uploadAudio(formData);
      setProgress(100);
      setResult(res);
      onComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleBatchUpload = async () => {
    if (!batchFile) {
      setError('Please select an Excel or CSV file');
      return;
    }

    setUploading(true);
    setProgress(10);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', batchFile);
      formData.append('model', model);

      setProgress(20);
      const res = await api.uploadBatch(formData);
      setProgress(100);
      setResult(res);
      onComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e) => { e.preventDefault(); e.currentTarget.classList.add('border-blue-400', 'bg-blue-50'); };
  const handleDragLeave = (e) => { e.currentTarget.classList.remove('border-blue-400', 'bg-blue-50'); };

  return (
    <>
      {/* Backdrop */}
      <div className="modal-backdrop" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Upload Survey Data</h2>
              <p className="text-sm text-gray-500 mt-0.5">Process new audit records with AI analysis</p>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Tabs */}
          <div className="px-6 pt-4">
            <div className="flex bg-gray-100 rounded-xl p-1">
              <button
                onClick={() => setActiveTab('single')}
                className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                  activeTab === 'single' ? 'bg-white shadow text-blue-700' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                🎙️ Single Upload
              </button>
              <button
                onClick={() => setActiveTab('batch')}
                className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                  activeTab === 'batch' ? 'bg-white shadow text-blue-700' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                📦 Batch Upload
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="px-6 py-5 space-y-4">
            {/* Model Selection */}
            <div>
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">AI Model for Analysis</label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {models.map(m => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>

            {activeTab === 'single' ? (
              <>
                {/* Audio File Drop Zone */}
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">
                    Audio File (.wav) <span className="text-gray-400 font-normal normal-case">— optional for demo</span>
                  </label>
                  <div
                    className="border-2 border-dashed border-gray-200 rounded-xl p-6 text-center cursor-pointer hover:border-blue-300 hover:bg-blue-50/50"
                    onClick={() => audioRef.current?.click()}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => {
                      e.preventDefault();
                      handleDragLeave(e);
                      const file = e.dataTransfer.files[0];
                      if (file) setAudioFile(file);
                    }}
                  >
                    <input
                      ref={audioRef}
                      type="file"
                      accept=".wav,.mp3,.m4a,.ogg"
                      className="hidden"
                      onChange={(e) => setAudioFile(e.target.files[0])}
                    />
                    {audioFile ? (
                      <div className="flex items-center justify-center gap-3">
                        <svg className="w-8 h-8 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                        </svg>
                        <div className="text-left">
                          <p className="text-sm font-semibold text-gray-800">{audioFile.name}</p>
                          <p className="text-xs text-gray-500">{(audioFile.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                        <button
                          onClick={(e) => { e.stopPropagation(); setAudioFile(null); }}
                          className="p-1 text-gray-400 hover:text-red-500"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ) : (
                      <>
                        <svg className="w-10 h-10 text-gray-300 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <p className="text-sm text-gray-500">Drop .wav file here or <span className="text-blue-600 font-semibold">browse</span></p>
                        <p className="text-xs text-gray-400 mt-1">Skip this for demo — mock transcript will be used</p>
                      </>
                    )}
                  </div>
                </div>

                {/* JSON Metadata */}
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">
                    JSON Metadata <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={jsonText}
                    onChange={(e) => setJsonText(e.target.value)}
                    placeholder='{"surveyor": "...", "date": "...", "id1": 12345, "audioanswers": [...], ...}'
                    className="w-full h-40 px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  />
                </div>

                {/* Upload button */}
                <button
                  onClick={handleSingleUpload}
                  disabled={uploading || !jsonText.trim()}
                  className="w-full btn-primary flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      Analyze Call
                    </>
                  )}
                </button>
              </>
            ) : (
              <>
                {/* Batch File Drop Zone */}
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">
                    Excel / CSV File <span className="text-red-500">*</span>
                  </label>
                  <div
                    className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center cursor-pointer hover:border-blue-300 hover:bg-blue-50/50"
                    onClick={() => batchRef.current?.click()}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => {
                      e.preventDefault();
                      handleDragLeave(e);
                      const file = e.dataTransfer.files[0];
                      if (file) setBatchFile(file);
                    }}
                  >
                    <input
                      ref={batchRef}
                      type="file"
                      accept=".xlsx,.xls,.csv"
                      className="hidden"
                      onChange={(e) => setBatchFile(e.target.files[0])}
                    />
                    {batchFile ? (
                      <div className="flex items-center justify-center gap-3">
                        <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <div className="text-left">
                          <p className="text-sm font-semibold text-gray-800">{batchFile.name}</p>
                          <p className="text-xs text-gray-500">{(batchFile.size / 1024).toFixed(1)} KB</p>
                        </div>
                        <button
                          onClick={(e) => { e.stopPropagation(); setBatchFile(null); }}
                          className="p-1 text-gray-400 hover:text-red-500"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ) : (
                      <>
                        <svg className="w-10 h-10 text-gray-300 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <p className="text-sm text-gray-500">Drop Excel/CSV file here or <span className="text-blue-600 font-semibold">browse</span></p>
                        <p className="text-xs text-gray-400 mt-1">Format: data_with_json.csv / .xlsx</p>
                      </>
                    )}
                  </div>
                </div>

                <button
                  onClick={handleBatchUpload}
                  disabled={uploading || !batchFile}
                  className="w-full btn-primary flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Processing batch...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                      </svg>
                      Process All Records
                    </>
                  )}
                </button>
              </>
            )}

            {/* Progress Bar */}
            {uploading && (
              <div>
                <div className="progress-bar">
                  <div className="progress-fill bg-blue-600" style={{ width: `${progress}%` }} />
                </div>
                <p className="text-xs text-gray-500 mt-1 text-center">{progress}% — Analyzing with AI...</p>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-xl border border-red-200">
                ❌ {error}
              </div>
            )}

            {/* Result */}
            {result && (
              <div className="bg-emerald-50 text-emerald-700 text-sm px-4 py-3 rounded-xl border border-emerald-200">
                ✅ {result.message}
                {result.analysis && (
                  <div className="mt-2 text-xs text-emerald-600">
                    Fraud: <strong>{result.analysis.fraud_type}</strong> | Score: <strong>{result.analysis.quality_score}</strong>/10
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
