import { createContext, useContext, useReducer, useCallback } from 'react';
import { fetchHealth } from '../api';

// ── State shape ───────────────────────────────────────────────────────────
const initialState = {
  // Health
  health: null,
  // Job
  jobInfo: null,       // { job_title, company, required_skills, preferred_skills }
  // Candidates
  candidateInfo: null, // { valid_candidates, total_loaded, source }
  // Analysis
  analysisResult: null,// summary returned by POST /analyze
  // Results
  results: null,       // full paginated results payload
  // UI
  loading: {},         // { [key]: bool }
  error: {},           // { [key]: string | null }
};

// ── Reducer ───────────────────────────────────────────────────────────────
function reducer(state, action) {
  switch (action.type) {
    case 'SET_HEALTH':       return { ...state, health: action.payload };
    case 'SET_JOB':          return { ...state, jobInfo: action.payload };
    case 'SET_CANDIDATES':   return { ...state, candidateInfo: action.payload };
    case 'SET_ANALYSIS':     return { ...state, analysisResult: action.payload };
    case 'SET_RESULTS':      return { ...state, results: action.payload };
    case 'SET_LOADING':
      return { ...state, loading: { ...state.loading, [action.key]: action.value } };
    case 'SET_ERROR':
      return { ...state, error: { ...state.error, [action.key]: action.value } };
    case 'RESET_PIPELINE':
      return { ...initialState };
    default:
      return state;
  }
}

// ── Context ───────────────────────────────────────────────────────────────
const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const setLoading = useCallback((key, value) =>
    dispatch({ type: 'SET_LOADING', key, value }), []);

  const setError = useCallback((key, value) =>
    dispatch({ type: 'SET_ERROR', key, value }), []);

  const refreshHealth = useCallback(async () => {
    try {
      const data = await fetchHealth();
      dispatch({ type: 'SET_HEALTH', payload: data });
    } catch {
      // Silently fail — health is non-critical
    }
  }, []);

  const setJob = useCallback((info) =>
    dispatch({ type: 'SET_JOB', payload: info }), []);

  const setCandidates = useCallback((info) =>
    dispatch({ type: 'SET_CANDIDATES', payload: info }), []);

  const setAnalysis = useCallback((info) =>
    dispatch({ type: 'SET_ANALYSIS', payload: info }), []);

  const setResults = useCallback((data) =>
    dispatch({ type: 'SET_RESULTS', payload: data }), []);

  const resetPipeline = useCallback(() =>
    dispatch({ type: 'RESET_PIPELINE' }), []);

  return (
    <AppContext.Provider value={{
      state,
      setLoading, setError,
      refreshHealth,
      setJob, setCandidates, setAnalysis, setResults,
      resetPipeline,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export const useApp = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
};
