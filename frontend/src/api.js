/**
 * Z-AUDIT — API Helper
 * Centralized API calls to the FastAPI backend.
 */

const API_BASE = '/api';

async function handleResponse(res) {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Dashboard stats
  getStats: () =>
    fetch(`${API_BASE}/stats`).then(handleResponse),

  // Leaderboard
  getLeaderboard: () =>
    fetch(`${API_BASE}/leaderboard`).then(handleResponse),

  // Heatmap
  getHeatmap: () =>
    fetch(`${API_BASE}/heatmap`).then(handleResponse),

  // Records (with filters + pagination)
  getRecords: ({ page = 1, limit = 20, fraud_type, min_score, max_score, search } = {}) => {
    const params = new URLSearchParams({ page, limit });
    if (fraud_type && fraud_type !== 'all') params.append('fraud_type', fraud_type);
    if (min_score != null) params.append('min_score', min_score);
    if (max_score != null) params.append('max_score', max_score);
    if (search) params.append('search', search);
    return fetch(`${API_BASE}/records?${params}`).then(handleResponse);
  },

  // Single record
  getRecord: (uid) =>
    fetch(`${API_BASE}/records/${uid}`).then(handleResponse),

  // Delete record
  deleteRecord: (uid) =>
    fetch(`${API_BASE}/records/${uid}`, { method: 'DELETE' }).then(handleResponse),

  // Re-analyze record with a different model (reuses existing transcript)
  reanalyzeRecord: (uid, model) =>
    fetch(`${API_BASE}/records/${uid}/reanalyze?model=${encodeURIComponent(model)}`, {
      method: 'POST',
    }).then(handleResponse),

  // Upload single audio + metadata
  uploadAudio: (formData) =>
    fetch(`${API_BASE}/upload-audio`, {
      method: 'POST',
      body: formData,
    }).then(handleResponse),

  // Batch upload
  uploadBatch: (formData) =>
    fetch(`${API_BASE}/upload-batch`, {
      method: 'POST',
      body: formData,
    }).then(handleResponse),

  // Export as Excel
  exportExcel: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.fraud_type && filters.fraud_type !== 'all') params.append('fraud_type', filters.fraud_type);
    if (filters.min_score != null) params.append('min_score', filters.min_score);
    if (filters.max_score != null) params.append('max_score', filters.max_score);
    return `${API_BASE}/export/excel?${params}`;
  },

  // Available models
  getModels: () =>
    fetch(`${API_BASE}/models`).then(handleResponse),

  // Test speaker diarization pipeline (GPU check)
  testSpeakerAnalysis: () =>
    fetch(`${API_BASE}/test-speaker-analysis`, { method: 'POST' }).then(handleResponse),
};
