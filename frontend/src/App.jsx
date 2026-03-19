import { useState, useEffect, useCallback } from 'react';
import { api } from './api';
import Dashboard from './components/Dashboard';
import UploadModal from './components/UploadModal';
import RecordDetail from './components/RecordDetail';

/**
 * Z-AUDIT — Main Application Shell
 * AI-powered audio quality auditing system for field survey calls.
 */
export default function App() {
  const [stats, setStats] = useState(null);
  const [records, setRecords] = useState([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [fraudFilter, setFraudFilter] = useState('all');
  const [minScore, setMinScore] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  // Modals
  const [showUpload, setShowUpload] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState(null);

  // Models
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');

  // Speaker Analysis Test
  const [speakerTestResult, setSpeakerTestResult] = useState(null);
  const [speakerTestLoading, setSpeakerTestLoading] = useState(false);
  const [showSpeakerTest, setShowSpeakerTest] = useState(false);

  // Load available models on mount
  useEffect(() => {
    api.getModels()
      .then(data => {
        setModels(data.models);
        setSelectedModel(data.default);
      })
      .catch(() => {});
  }, []);

  // Fetch stats
  const fetchStats = useCallback(async () => {
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (err) {
      console.error('Stats error:', err);
    }
  }, []);

  // Fetch records
  const fetchRecords = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getRecords({
        page,
        limit: 20,
        fraud_type: fraudFilter,
        min_score: minScore > 0 ? minScore : undefined,
        search: searchQuery || undefined,
      });
      setRecords(data.records);
      setTotalRecords(data.total);
      setTotalPages(data.total_pages);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Records error:', err);
    } finally {
      setLoading(false);
    }
  }, [page, fraudFilter, minScore, searchQuery]);

  // Load data on mount and when filters change
  useEffect(() => {
    fetchStats();
    fetchRecords();
  }, [fetchStats, fetchRecords]);

  // Refresh everything
  const refreshAll = () => {
    fetchStats();
    fetchRecords();
  };

  // Handle record deletion
  const handleDelete = async (uid) => {
    if (!confirm(`Delete record UID ${uid}?`)) return;
    try {
      await api.deleteRecord(uid);
      refreshAll();
      if (selectedRecord?.uid === uid) setSelectedRecord(null);
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  // Handle export
  const handleExport = () => {
    const url = api.exportExcel({ fraud_type: fraudFilter, min_score: minScore > 0 ? minScore : undefined });
    window.open(url, '_blank');
  };

  // Test speaker diarization GPU pipeline
  const handleTestSpeaker = async () => {
    setSpeakerTestLoading(true);
    setSpeakerTestResult(null);
    setShowSpeakerTest(true);
    try {
      const result = await api.testSpeakerAnalysis();
      setSpeakerTestResult(result);
    } catch (err) {
      setSpeakerTestResult({ error: err.message });
    } finally {
      setSpeakerTestLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="header-gradient text-white shadow-xl">
        <div className="max-w-[1440px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 bg-white/20 backdrop-blur rounded-xl flex items-center justify-center shadow-inner">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Z-AUDIT</h1>
              <p className="text-blue-200 text-xs font-medium">AI Audio Quality Auditing</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Model Selector */}
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-white/15 backdrop-blur text-white text-sm rounded-lg border border-white/20 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-white/30 cursor-pointer"
              title="Select AI Model for Analysis"
            >
              {models.map(m => (
                <option key={m.id} value={m.id} className="text-gray-900">{m.name}</option>
              ))}
            </select>

            <button
              onClick={handleTestSpeaker}
              disabled={speakerTestLoading}
              className="bg-white/15 backdrop-blur hover:bg-white/25 text-white text-sm font-semibold px-4 py-2 rounded-lg border border-white/20 flex items-center gap-2"
              title="Test Speaker Diarization (GPU)"
            >
              🔊 {speakerTestLoading ? 'Testing...' : 'Test GPU'}
            </button>

            <button
              onClick={handleExport}
              className="bg-white/15 backdrop-blur hover:bg-white/25 text-white text-sm font-semibold px-4 py-2 rounded-lg border border-white/20 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export
            </button>

            <button
              onClick={() => setShowUpload(true)}
              className="bg-white text-blue-800 hover:bg-blue-50 text-sm font-bold px-5 py-2 rounded-lg shadow-lg shadow-black/10 flex items-center gap-2 pulse-glow"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Upload
            </button>
          </div>
        </div>
      </header>

      {/* Main Dashboard */}
      <main className="max-w-[1440px] mx-auto px-6 py-6">
        <Dashboard
          stats={stats}
          records={records}
          totalRecords={totalRecords}
          totalPages={totalPages}
          page={page}
          loading={loading}
          error={error}
          fraudFilter={fraudFilter}
          minScore={minScore}
          searchQuery={searchQuery}
          onFilterChange={setFraudFilter}
          onMinScoreChange={setMinScore}
          onSearchChange={setSearchQuery}
          onPageChange={setPage}
          onRecordClick={setSelectedRecord}
          onDelete={handleDelete}
        />
      </main>

      {/* Upload Modal */}
      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onSuccess={refreshAll}
          selectedModel={selectedModel}
          models={models}
        />
      )}

      {/* Record Detail Panel */}
      {selectedRecord && (
        <RecordDetail
          record={selectedRecord}
          onClose={() => setSelectedRecord(null)}
          onDelete={handleDelete}
          onRecordUpdate={(updatedRecord) => {
            setSelectedRecord(updatedRecord);
            refreshAll();
          }}
        />
      )}

      {/* Speaker Test Modal */}
      {showSpeakerTest && (
        <>
          <div className="fixed inset-0 bg-black/50 z-50" onClick={() => setShowSpeakerTest(false)} />
          <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-2xl shadow-2xl z-50 w-[500px] max-h-[80vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">🔊 Speaker Diarization Test</h2>
              <button onClick={() => setShowSpeakerTest(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {speakerTestLoading && (
              <div className="text-center py-8">
                <div className="w-8 h-8 border-3 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-gray-500">Loading pyannote model & running diarization...</p>
                <p className="text-xs text-gray-400 mt-1">First run takes ~10-15s to load the model</p>
              </div>
            )}

            {speakerTestResult && !speakerTestLoading && (
              <div className="space-y-3">
                {/* GPU Status */}
                <div className={`p-3 rounded-lg border ${speakerTestResult.gpu_available ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                  <p className="text-sm font-semibold">
                    {speakerTestResult.gpu_available ? '✅ GPU Available' : '❌ No GPU Detected'}
                  </p>
                  {speakerTestResult.gpu_name && (
                    <p className="text-xs text-gray-600 mt-1">GPU: {speakerTestResult.gpu_name}</p>
                  )}
                  <p className="text-xs text-gray-500">PyTorch: {speakerTestResult.torch_version} | CUDA: {speakerTestResult.cuda_version || 'N/A'}</p>
                </div>

                {/* Pipeline Status */}
                <div className={`p-3 rounded-lg border ${speakerTestResult.pipeline_loaded ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                  <p className="text-sm font-semibold">
                    {speakerTestResult.pipeline_loaded ? '✅ Pipeline Loaded' : '❌ Pipeline Failed'}
                  </p>
                  {speakerTestResult.test_audio && (
                    <p className="text-xs text-gray-600 mt-1">Test file: {speakerTestResult.test_audio} ({speakerTestResult.test_audio_size_mb}MB)</p>
                  )}
                  {speakerTestResult.time_seconds != null && (
                    <p className="text-xs text-gray-500">Processing time: {speakerTestResult.time_seconds}s</p>
                  )}
                </div>

                {/* Diarization Result */}
                {speakerTestResult.diarization_result && (
                  <div className="p-3 rounded-lg border bg-violet-50 border-violet-200">
                    <p className="text-sm font-semibold text-violet-800">
                      🎙️ Detected {speakerTestResult.diarization_result.num_speakers} speaker(s)
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      {speakerTestResult.diarization_result.speaker_turns} turns | 
                      {speakerTestResult.diarization_result.total_duration}s total duration
                    </p>
                    {Object.entries(speakerTestResult.diarization_result.speakers || {}).map(([label, data]) => (
                      <div key={label} className="mt-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-gray-700">{label}</span>
                          <span className="text-xs text-gray-500">{data.total_time}s ({data.percentage}%)</span>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden mt-1">
                          <div className="h-full bg-violet-500 rounded-full" style={{ width: `${data.percentage}%` }} />
                        </div>
                      </div>
                    ))}
                    <p className="text-[10px] text-gray-400 mt-2">Source: {speakerTestResult.diarization_result.analysis_source}</p>
                  </div>
                )}

                {/* Error */}
                {speakerTestResult.error && (
                  <div className="p-3 rounded-lg border bg-red-50 border-red-200">
                    <p className="text-sm font-semibold text-red-800">❌ Error</p>
                    <p className="text-xs text-red-700 mt-1 break-words">{speakerTestResult.error}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
