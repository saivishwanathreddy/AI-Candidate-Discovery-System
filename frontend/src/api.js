import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 300_000, // 5 min — analysis can take long on 100K candidates
  headers: { 'Content-Type': 'application/json' },
});

// ── Response interceptor — normalise errors ──────────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail =
      err?.response?.data?.detail ||
      err?.response?.data?.message ||
      err?.message ||
      'An unexpected error occurred.';
    err.userMessage = detail;
    return Promise.reject(err);
  }
);

// ──────────────────────────────────────────────────────────────────────────
// Health
// ──────────────────────────────────────────────────────────────────────────
export const fetchHealth = () => api.get('/health').then((r) => r.data);

// ──────────────────────────────────────────────────────────────────────────
// Upload Job Description (.docx)
// ──────────────────────────────────────────────────────────────────────────
export const uploadJob = (file) => {
  if (!file) {
    // Use server-side default JD
    return api.post('/upload-job').then((r) => r.data);
  }
  const form = new FormData();
  form.append('file', file);
  return api
    .post('/upload-job', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    .then((r) => r.data);
};

// ──────────────────────────────────────────────────────────────────────────
// Upload Candidates (.jsonl / .json)
// ──────────────────────────────────────────────────────────────────────────
export const uploadCandidates = ({ file, useSample, maxRecords, validate = true }) => {
  const params = new URLSearchParams();
  if (useSample) params.set('use_sample', 'true');
  if (maxRecords) params.set('max_records', String(maxRecords));
  if (!validate) params.set('validate', 'false');

  if (!file) {
    return api.post(`/upload-candidates?${params}`).then((r) => r.data);
  }
  const form = new FormData();
  form.append('file', file);
  return api
    .post(`/upload-candidates?${params}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};

// ──────────────────────────────────────────────────────────────────────────
// Analyze
// ──────────────────────────────────────────────────────────────────────────
export const runAnalysis = (weights = {}) =>
  api.post('/analyze', weights).then((r) => r.data);

// ──────────────────────────────────────────────────────────────────────────
// Results (paginated)
// ──────────────────────────────────────────────────────────────────────────
export const fetchResults = ({ page = 1, pageSize = 25, minScore = 0 } = {}) =>
  api
    .get('/results', { params: { page, page_size: pageSize, min_score: minScore } })
    .then((r) => r.data);

// ──────────────────────────────────────────────────────────────────────────
// Single candidate detail
// ──────────────────────────────────────────────────────────────────────────
export const fetchCandidate = (candidateId) =>
  api.get(`/candidate/${candidateId}`).then((r) => r.data);

export default api;
