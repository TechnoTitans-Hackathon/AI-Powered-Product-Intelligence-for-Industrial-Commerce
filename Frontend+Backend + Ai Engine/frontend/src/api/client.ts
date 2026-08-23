import axios from 'axios';
import {
  ProductItem,
  ProcessingJobItem,
  ValidationIssue,
  AnalyticsSummary,
  RecentActivityItem,
  RecentlyProcessedItem,
  EvidenceItem,
  SourceDoc,
} from '../types';

export enum AIProcessingMode {
  AUTO = "AUTO",
  FAST = "FAST",
  DEEP = "DEEP",
  LOCAL = "LOCAL"
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to automatically attach active tenant and JWT auth token
api.interceptors.request.use((config) => {
  const tenantId = localStorage.getItem('active_tenant_id') || 'demo';
  const token = localStorage.getItem('auth_token');

  if (tenantId) {
    config.headers['X-Tenant-ID'] = tenantId;
  }
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// ─── Auth & Tenant API ────────────────────────────────────────────────────────

export interface TenantInfo {
  id: string;
  name: string;
  slug: string;
  industry: string;
  tier: string;
  created_at?: string;
}

export interface UserInfo {
  id: string;
  email: string;
  name: string;
  tenant_id: string;
  role: string;
  company_name?: string;
}

export const registerCompany = async (data: {
  name: string;
  email: string;
  company_name: string;
  industry?: string;
  password?: string;
}): Promise<{ access_token: string; tenant: TenantInfo; user: UserInfo }> => {
  const res = await api.post('/auth/register', data);
  if (res.data.access_token) {
    localStorage.setItem('auth_token', res.data.access_token);
    localStorage.setItem('active_tenant_id', res.data.tenant.id);
    localStorage.setItem('active_tenant_name', res.data.tenant.name);
  }
  return res.data;
};

export const loginUser = async (data: {
  email: string;
  password?: string;
  tenant_id?: string;
}): Promise<{ access_token: string; tenant: TenantInfo; user: UserInfo }> => {
  const res = await api.post('/auth/login', data);
  if (res.data.access_token) {
    localStorage.setItem('auth_token', res.data.access_token);
    localStorage.setItem('active_tenant_id', res.data.tenant.id);
    localStorage.setItem('active_tenant_name', res.data.tenant.name);
  }
  return res.data;
};

export const getTenantsList = async (): Promise<TenantInfo[]> => {
  const res = await api.get<TenantInfo[]>('/auth/tenants');
  return res.data;
};

export const switchActiveTenant = async (tenantId: string): Promise<{ access_token: string; tenant: TenantInfo }> => {
  const res = await api.post(`/auth/switch-tenant`, { tenant_id: tenantId });
  if (res.data.access_token) {
    localStorage.setItem('auth_token', res.data.access_token);
    localStorage.setItem('active_tenant_id', res.data.tenant.id);
    localStorage.setItem('active_tenant_name', res.data.tenant.name);
  }
  return res.data;
};

export const getAuthMe = async (): Promise<{ user: UserInfo; tenant: TenantInfo }> => {
  const res = await api.get('/auth/me');
  return res.data;
};

// ─── Products API ─────────────────────────────────────────────────────────────

export const getProducts = async (params?: {
  skip?: number;
  limit?: number;
  search?: string;
  category?: string;
  status?: string;
  confidence_level?: string;
}): Promise<ProductItem[]> => {
  const res = await api.get<ProductItem[]>('/products', { params });
  return res.data;
};

export const getProductById = async (id: string): Promise<ProductItem> => {
  const res = await api.get<ProductItem>(`/products/${id}`);
  return res.data;
};

export const getProductIntelligence = async (id: string): Promise<any> => {
  const res = await api.get(`/products/${id}/intelligence`);
  return res.data;
};

export const createProduct = async (data: {
  name: string;
  sku?: string;
  mpn?: string;
  brand?: string;
  manufacturer?: string;
  category?: string;
  subcategory?: string;
  industry?: string;
  description?: string;
  imageUrl?: string;
  ai_mode?: AIProcessingMode;
}): Promise<ProductItem> => {
  const res = await api.post<ProductItem>('/products', data);
  return res.data;
};

export const createProductFromUrl = async (data: {
  url: string;
  product_name?: string;
  sku?: string;
  category?: string;
  note?: string;
  ai_mode?: AIProcessingMode;
}): Promise<ProductItem> => {
  const res = await api.post<ProductItem>('/products/from-url', data);
  return res.data;
};

export const updateProduct = async (id: string, data: Partial<ProductItem>): Promise<ProductItem> => {
  const res = await api.put<ProductItem>(`/products/${id}`, data);
  return res.data;
};

export const deleteProduct = async (id: string): Promise<{ message: string; id: string }> => {
  const res = await api.delete(`/products/${id}`);
  return res.data;
};

export const triggerProductProcess = async (
  id: string,
  background: boolean = false,
  ai_mode?: AIProcessingMode
): Promise<{ message: string; job_id: string; status: string; product?: ProductItem; ai_mode?: string }> => {
  const res = await api.post(`/products/${id}/process`, null, { params: { background, ai_mode } });
  return res.data;
};

export const triggerProductReprocess = async (
    id: string,
    ai_mode?: AIProcessingMode
): Promise<{ message: string; job_id: string; status: string; product: ProductItem; ai_mode?: string }> => {
  const res = await api.post(`/products/${id}/reprocess`, null, { params: { ai_mode } });
  return res.data;
};

export const exportProductXlsx = async (id: string): Promise<void> => {
  try {
    const res = await api.get(`/products/${id}/export/xlsx`, {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;

    // Extract filename from Content-Disposition header if possible
    const contentDisposition = res.headers['content-disposition'];
    let filename = `Unihack_Export_${id}.xlsx`;
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
      if (filenameMatch && filenameMatch.length === 2) {
        filename = filenameMatch[1];
      }
    }

    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (error: any) {
    if (error.response && error.response.data instanceof Blob) {
      const text = await error.response.data.text();
      try {
        const json = JSON.parse(text);
        throw new Error(json.detail || 'Export failed');
      } catch (e) {
        throw new Error('Export failed');
      }
    }
    throw error;
  }
};

// ─── File Uploads API ─────────────────────────────────────────────────────────

export const uploadSourceFile = async (file: File, productId?: string): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);
  if (productId) {
    formData.append('product_id', productId);
  }
  const res = await api.post('/uploads', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const uploadBatchCatalog = async (
  file: File,
  autoProcess: boolean = true,
  ai_mode: AIProcessingMode = AIProcessingMode.AUTO
): Promise<{
  batch_id: string;
  filename: string;
  total_rows: number;
  imported_count: number;
  skipped_count: number;
  headers_detected: string[];
  errors: string[];
  job_ids: string[];
  product_ids: string[];
  message: string;
}> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('auto_process', String(autoProcess));
  formData.append('ai_mode', ai_mode);

  const res = await api.post('/products/batch-upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

// ─── Jobs & Batches API ───────────────────────────────────────────────────────

export const getJobs = async (params?: { skip?: number; limit?: number; status?: string }): Promise<ProcessingJobItem[]> => {
  const res = await api.get<ProcessingJobItem[]>('/jobs', { params });
  return res.data;
};

export const getJobById = async (jobId: string): Promise<ProcessingJobItem> => {
  const res = await api.get<ProcessingJobItem>(`/jobs/${jobId}`);
  return res.data;
};

export const submitBatchProcessing = async (productIds: string[], ai_mode: AIProcessingMode = AIProcessingMode.AUTO): Promise<{ message: string; job_ids: string[]; total: number }> => {
  const res = await api.post('/batch', { product_ids: productIds, ai_mode });
  return res.data;
};

export const getBatchSummary = async (): Promise<{
  total_jobs: number;
  completed: number;
  failed: number;
  processing: number;
  queued: number;
  remaining: number;
}> => {
  const res = await api.get('/batch/summary');
  return res.data;
};

// ─── Validation Center API ────────────────────────────────────────────────────

export const getValidationIssues = async (params?: {
  product_id?: string;
  severity?: string;
  type?: string;
  resolved?: boolean;
  skip?: number;
  limit?: number;
}): Promise<ValidationIssue[]> => {
  const res = await api.get<ValidationIssue[]>('/validation', { params });
  return res.data;
};

export const getValidationSummary = async (): Promise<{
  total_issues: number;
  resolved: number;
  unresolved: number;
  conflicts: number;
  missing_fields: number;
  critical: number;
  high: number;
  needs_attention: number;
}> => {
  const res = await api.get('/validation/summary');
  return res.data;
};

export const resolveValidationIssue = async (
  issueId: string,
  data: { resolved: boolean; corrected_value?: string; reviewer?: string }
): Promise<ValidationIssue> => {
  const res = await api.post<ValidationIssue>(`/validation/${issueId}/resolve`, data);
  return res.data;
};

// ─── Explainability & Sources API ─────────────────────────────────────────────

export const getExplainability = async (productId: string): Promise<{
  product_id: string;
  product_name: string;
  sources: SourceDoc[];
  evidence: EvidenceItem[];
  field_provenance: any[];
  overall_confidence: number;
  confidence_level: string;
  missing_fields_count: number;
  conflict_fields_count: number;
}> => {
  const res = await api.get(`/explainability/${productId}`);
  return res.data;
};

export const getProductSources = async (productId: string): Promise<SourceDoc[]> => {
  const res = await api.get<SourceDoc[]>(`/explainability/${productId}/sources`);
  return res.data;
};

// ─── Analytics API ────────────────────────────────────────────────────────────

export const getAnalyticsSummary = async (): Promise<AnalyticsSummary> => {
  const res = await api.get<AnalyticsSummary>('/analytics/summary');
  return res.data;
};

export const getRecentActivity = async (limit: number = 20): Promise<RecentActivityItem[]> => {
  const res = await api.get<RecentActivityItem[]>('/analytics/recent-activity', { params: { limit } });
  return res.data;
};

export const getRecentlyProcessed = async (limit: number = 10): Promise<RecentlyProcessedItem[]> => {
  const res = await api.get<RecentlyProcessedItem[]>('/analytics/recently-processed', { params: { limit } });
  return res.data;
};

export const getProcessingTrends = async (days: number = 7): Promise<{
  period_days: number;
  daily_breakdown: Array<{ date: string; total: number; completed: number; failed: number }>;
  total_processed: number;
}> => {
  const res = await api.get('/analytics/trends', { params: { days } });
  return res.data;
};

