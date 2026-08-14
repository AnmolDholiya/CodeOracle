import axios from 'axios';
import { API_BASE_URL } from '../config';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120 seconds to easily handle Render free tier cold-starts
});

export const formatApiError = (err, fallbackMsg = 'An error occurred.') => {
  if (!err) return fallbackMsg;
  if (err.code === 'ECONNABORTED' || (err.message && err.message.toLowerCase().includes('timeout'))) {
    return 'Server connection timed out (Render cold-start in progress). Please wait a few seconds and try again.';
  }
  const detail = err.response?.data?.detail;
  if (!detail) return err.message || fallbackMsg;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(item => (typeof item === 'object' ? (item.msg || JSON.stringify(item)) : String(item))).join('; ');
  }
  if (typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return String(detail);
};

export const checkHealth = async () => {
  try {
    const response = await api.get('/api/health');
    return response.data;
  } catch (error) {
    console.error('API Health Check Error:', error);
    throw error;
  }
};

export const uploadProjectZip = async (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/api/projects/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
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
  });
  return response.data;
};

export const deleteProject = async (projectId) => {
  const response = await api.delete(`/api/projects/${projectId}`);
  return response.data;
};

export const getProjectInfo = async (projectId) => {
  const response = await api.get(`/api/projects/${projectId}`);
  return response.data;
};

export const getProjectStatus = async (projectId) => {
  const response = await api.get(`/api/projects/${projectId}/status`);
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

export default api;
