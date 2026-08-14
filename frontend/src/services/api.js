import axios from 'axios';
import { API_BASE_URL } from '../config';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds for normal API calls (backend is already awake)
});

// ─── Error Classification ───────────────────────────────────────────

/**
 * Classifies and formats API errors into structured { type, message } objects.
 * Types: COLD_START, TIMEOUT, BACKEND_UNAVAILABLE, UPLOAD_ERROR,
 *        VALIDATION_ERROR, CORS_ERROR, RATE_LIMIT, PROCESSING_ERROR, UNKNOWN
 */
export const formatApiError = (err, fallbackMsg = 'An error occurred.') => {
  if (!err) return { type: 'UNKNOWN', message: fallbackMsg };

  // Network-level failures (no response received)
  if (!err.response) {
    if (err.code === 'ECONNABORTED' || (err.message && err.message.toLowerCase().includes('timeout'))) {
      return { type: 'TIMEOUT', message: 'Request timed out. The server may still be processing.' };
    }
    if (err.code === 'ERR_NETWORK' || err.message === 'Network Error') {
      return { type: 'BACKEND_UNAVAILABLE', message: 'Cannot reach the CodeOracle backend. It may be starting up.' };
    }
    return { type: 'BACKEND_UNAVAILABLE', message: err.message || fallbackMsg };
  }

  // HTTP response received — classify by status code
  const status = err.response.status;
  const detail = err.response?.data?.detail;
  const msg = typeof detail === 'string' ? detail
    : Array.isArray(detail) ? detail.map(item => (typeof item === 'object' ? (item.msg || JSON.stringify(item)) : String(item))).join('; ')
    : (detail && typeof detail === 'object') ? (detail.msg || detail.message || JSON.stringify(detail))
    : (err.message || fallbackMsg);

  if (status === 400) return { type: 'VALIDATION_ERROR', message: msg };
  if (status === 413) return { type: 'VALIDATION_ERROR', message: msg || 'ZIP archive exceeds the supported upload size limit.' };
  if (status === 401 || status === 403) return { type: 'CORS_ERROR', message: msg };
  if (status === 404) return { type: 'PROCESSING_ERROR', message: msg };
  if (status === 429) return { type: 'RATE_LIMIT', message: msg };
  if (status === 502 || status === 503 || status === 504) return { type: 'COLD_START', message: msg };
  if (status >= 500) return { type: 'PROCESSING_ERROR', message: msg };

  return { type: 'UNKNOWN', message: msg };
};

/**
 * Legacy-compatible string error formatter (for components that haven't migrated).
 */
export const formatApiErrorMessage = (err, fallbackMsg = 'An error occurred.') => {
  return formatApiError(err, fallbackMsg).message;
};

// ─── Backend Wake-Up (Cold-Start Handling) ──────────────────────────

/**
 * Pings GET /api/health with exponential backoff to wake the Render Free backend.
 * Returns the health data on success, throws on total failure.
 *
 * @param {function} onProgress - Optional callback: (stage: string, attempt: number, maxAttempts: number) => void
 */
export const wakeUpBackend = async (onProgress) => {
  const MAX_ATTEMPTS = 5;
  const DELAYS = [2000, 4000, 8000, 10000, 10000]; // ms between retries
  const HEALTH_TIMEOUT = 8000; // 8s per health ping (short, for cold-start detection)

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    try {
      if (onProgress) {
        if (attempt === 1) onProgress('connecting', attempt, MAX_ATTEMPTS);
        else onProgress('retrying', attempt, MAX_ATTEMPTS);
      }

      const response = await axios.get(`${API_BASE_URL}/api/health`, {
        timeout: HEALTH_TIMEOUT,
      });

      if (response.data && (response.data.status === 'healthy' || response.data.status === 'ok')) {
        if (onProgress) onProgress('ready', attempt, MAX_ATTEMPTS);
        return response.data;
      }
    } catch (err) {
      console.warn(`[WakeUp] Health check attempt ${attempt}/${MAX_ATTEMPTS} failed:`, err.message);

      if (attempt < MAX_ATTEMPTS) {
        if (onProgress) onProgress('waking', attempt, MAX_ATTEMPTS);
        await new Promise(resolve => setTimeout(resolve, DELAYS[attempt - 1]));
      }
    }
  }

  // All attempts exhausted
  throw new Error('BACKEND_WAKE_FAILED');
};

// ─── Health Check ───────────────────────────────────────────────────

export const checkHealth = async () => {
  try {
    const response = await api.get('/api/health', { timeout: 10000 });
    return response.data;
  } catch (error) {
    console.error('API Health Check Error:', error);
    throw error;
  }
};

// ─── Project Upload ─────────────────────────────────────────────────

export const uploadProjectZip = async (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/api/projects/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000, // 300s (5 min) for large file upload transfer over network
    onUploadProgress: (progressEvent) => {
      if (onUploadProgress && progressEvent.total) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onUploadProgress(percentCompleted);
      }
    },
  });

  return response.data;
};

export const uploadGithubRepo = async (repoUrl) => {
  const response = await api.post('/api/projects/upload_github', {
    repo_url: repoUrl
  }, {
    timeout: 60000
  });
  return response.data;
};

// ─── Project Operations ─────────────────────────────────────────────

export const deleteProject = async (projectId) => {
  const response = await api.delete(`/api/projects/${projectId}`);
  return response.data;
};

export const getProjectInfo = async (projectId) => {
  const response = await api.get(`/api/projects/${projectId}`);
  return response.data;
};

export const getProjectStatus = async (projectId) => {
  const response = await api.get(`/api/projects/${projectId}/status`, {
    timeout: 15000
  });
  return response.data;
};

export const analyzeProject = async (projectId) => {
  const response = await api.post(`/api/projects/${projectId}/analyze`);
  return response.data;
};

export const getProjectAnalysis = async (projectId) => {
  const response = await api.get(`/api/projects/${projectId}/analyze`);
  return response.data;
};

export const getProjectDependencies = async (projectId) => {
  const response = await api.get(`/api/projects/${projectId}/dependencies`);
  return response.data;
};

// ─── AI-Powered Features ────────────────────────────────────────────

export const refactorFile = async (projectId, filePath, forceRefresh = false) => {
  const response = await api.post(`/api/projects/${projectId}/refactor/file`, {
    file_path: filePath,
    force_refresh: forceRefresh
  });
  return response.data;
};

export const refactorFunction = async (projectId, filePath, functionName, forceRefresh = false) => {
  const response = await api.post(`/api/projects/${projectId}/refactor/function`, {
    file_path: filePath,
    function_name: functionName,
    force_refresh: forceRefresh
  });
  return response.data;
};

export const saveRefactoredCode = async (projectId, filePath, refactoredCode) => {
  const response = await api.post(`/api/projects/${projectId}/refactor/save`, {
    file_path: filePath,
    refactored_code: refactoredCode
  });
  return response.data;
};

export const analyzeBreakingChanges = async (projectId, filePath, modifiedCode = '', forceRefresh = false) => {
  const response = await api.post(`/api/projects/${projectId}/breaking-changes/analyze`, {
    file_path: filePath,
    modified_code: modifiedCode,
    force_refresh: forceRefresh
  });
  return response.data;
};

export const explainBreakingChanges = async (projectId, filePath, changes = [], forceRefresh = false) => {
  const response = await api.post(`/api/projects/${projectId}/breaking-changes/explain`, {
    file_path: filePath,
    changes: changes,
    force_refresh: forceRefresh
  });
  return response.data;
};

// ─── Improvements & Recommendations ─────────────────────────────────

export const getProjectImprovements = async (projectId) => {
  const response = await api.get(`/api/projects/${projectId}/improvements`);
  return response.data;
};

export const explainProjectImprovements = async (projectId, focusCategory = null) => {
  const response = await api.post(`/api/projects/${projectId}/improvements/explain`, {
    focus_category: focusCategory
  });
  return response.data;
};

// ─── CodeOracle AI Chatbot ──────────────────────────────────────────

export const sendChatMessage = async (projectId, message, conversationId = null, selectedFile = null, selectedFunction = null) => {
  const response = await api.post('/api/chat', {
    project_id: projectId,
    message: message,
    conversation_id: conversationId,
    selected_file: selectedFile,
    selected_function: selectedFunction
  });
  return response.data;
};

export default api;
