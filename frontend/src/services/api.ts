import type {
  User,
  TokenResponse,
  AssetRegistrationResponse,
  AssetSummary,
  AssetDetail,
  Receipt,
  VerificationResponse,
  ReceiptVerifyResponse,
  RobustnessBenchmarks,
  AsyncJobStatus,
  AsyncJobSubmission,
  AsyncJobListResponse,
  GlobalCase,
  CaseStatus,
  CaseReport,
  SimilarityCompareResult,
  SimilaritySearchResult,
} from '../types';
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers || {});

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    let errorData = null;
    try {
      errorData = await response.json();
      if (typeof errorData?.detail === 'string') {
        errorDetail = errorData.detail;
      } else if (Array.isArray(errorData?.detail)) {
        errorDetail = errorData.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
      } else if (errorData?.message) {
        errorDetail = errorData.message;
      }
    } catch {
      if (response.statusText) {
        errorDetail = response.statusText;
      }
    }
    throw new ApiError(response.status, errorDetail, errorData);
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json() as Promise<T>;
  }
  return response as unknown as T;
}

// ----------------- Authentication -----------------
export async function registerUser(
  email: string,
  password: string,
  fullName: string
): Promise<User> {
  return request<User>('/api/v1/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
}

export async function loginUser(
  email: string,
  password: string
): Promise<TokenResponse> {
  return request<TokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
}

export async function getCurrentUser(token: string): Promise<User> {
  return request<User>('/api/v1/auth/me', {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
}

// ----------------- Asset Registration & Vault -----------------
export interface RegisterAssetParams {
  file: File;
  title: string;
  ownershipDeclaration: string;
  algorithm: string;
  alpha: number;
  category?: string;
  country?: string;
  licenseType?: string;
  attributionText?: string;
  idempotencyKey?: string;
}

export async function registerAsset(
  params: RegisterAssetParams,
  token: string
): Promise<AssetRegistrationResponse> {
  const formData = new FormData();
  formData.append('file', params.file);
  formData.append('title', params.title);
  formData.append('ownership_declaration', params.ownershipDeclaration);
  formData.append('algorithm', params.algorithm);
  formData.append('alpha', params.alpha.toString());
  if (params.category) formData.append('category', params.category);
  if (params.country) formData.append('country', params.country);
  if (params.licenseType) formData.append('license_type', params.licenseType);
  if (params.attributionText) formData.append('attribution_text', params.attributionText);

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };

  if (params.idempotencyKey) {
    headers['Idempotency-Key'] = params.idempotencyKey;
  }

  return request<AssetRegistrationResponse>('/api/v1/assets/register', {
    method: 'POST',
    headers,
    body: formData,
  });
}

export async function listAssets(
  token: string,
  skip = 0,
  limit = 50,
  category?: string,
  country?: string
): Promise<AssetSummary[]> {
  const params = new URLSearchParams();
  params.append('skip', skip.toString());
  params.append('limit', limit.toString());
  if (category && category !== 'All') params.append('category', category);
  if (country && country !== 'All') params.append('country', country);

  return request<AssetSummary[]>(`/api/v1/assets?${params.toString()}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getAssetDetail(
  token: string,
  assetId: number
): Promise<AssetDetail> {
  return request<AssetDetail>(`/api/v1/assets/${assetId}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getReceipt(
  token: string,
  assetId: number
): Promise<Receipt> {
  return request<Receipt>(`/api/v1/assets/${assetId}/receipt`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function downloadReceiptJson(
  token: string,
  assetId: number
): Promise<Blob> {
  const receipt = await getReceipt(token, assetId);
  return new Blob([JSON.stringify(receipt, null, 2)], {
    type: 'application/json',
  });
}

export async function registerAssetAsync(
  params: RegisterAssetParams,
  token: string
): Promise<AsyncJobSubmission> {
  const formData = new FormData();
  formData.append('file', params.file);
  formData.append('title', params.title);
  formData.append('ownership_declaration', params.ownershipDeclaration);
  formData.append('algorithm', params.algorithm);
  formData.append('alpha', params.alpha.toString());
  if (params.category) formData.append('category', params.category);
  if (params.country) formData.append('country', params.country);
  if (params.licenseType) formData.append('license_type', params.licenseType);
  if (params.attributionText) formData.append('attribution_text', params.attributionText);

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };

  if (params.idempotencyKey) {
    headers['Idempotency-Key'] = params.idempotencyKey;
  }

  return request<AsyncJobSubmission>('/api/v1/assets/register-async', {
    method: 'POST',
    headers,
    body: formData,
  });
}

export async function getJobStatus(
  jobId: string,
  token: string
): Promise<AsyncJobStatus> {
  return request<AsyncJobStatus>(`/api/v1/jobs/${jobId}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function listJobs(
  token: string,
  skip: number = 0,
  limit: number = 50
): Promise<AsyncJobListResponse> {
  return request<AsyncJobListResponse>(`/api/v1/jobs?skip=${skip}&limit=${limit}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function downloadWatermarkedImage(
  token: string,
  assetId: number,
  presigned: boolean = false
): Promise<Blob> {
  const query = presigned ? '?presigned=true' : '';
  const url = `${API_BASE_URL}/api/v1/assets/${assetId}/download/watermarked${query}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    let errorMsg = `Download failed with status ${response.status}`;
    try {
      const err = await response.json();
      if (err?.detail) errorMsg = err.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return response.blob();
}

// ----------------- Ownership Verification -----------------
export interface VerifyParams {
  file: File;
  algorithm?: string;
  alpha?: number;
  expectedAssetId?: number;
  receiptPayload?: string;
  receiptSignature?: string;
}

export async function verifyImage(
  params: VerifyParams,
  token?: string | null
): Promise<VerificationResponse> {
  const formData = new FormData();
  formData.append('file', params.file);
  formData.append('algorithm', params.algorithm || 'dct_svd');
  formData.append('alpha', (params.alpha ?? 0.1).toString());

  if (params.expectedAssetId !== undefined && params.expectedAssetId !== null) {
    formData.append('expected_asset_id', params.expectedAssetId.toString());
  }
  if (params.receiptPayload) {
    formData.append('receipt_payload', params.receiptPayload);
  }
  if (params.receiptSignature) {
    formData.append('receipt_signature', params.receiptSignature);
  }

  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return request<VerificationResponse>('/api/v1/verify', {
    method: 'POST',
    headers,
    body: formData,
  });
}

// ----------------- Public Receipt Verification -----------------
export async function verifyReceiptRecord(
  payload: Record<string, any>,
  signature: string
): Promise<ReceiptVerifyResponse> {
  return request<ReceiptVerifyResponse>('/api/v1/assets/receipts/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      receipt_payload: payload,
      receipt_signature: signature,
    }),
  });
}

// ----------------- Robustness Benchmarks -----------------
export async function fetchRobustnessBenchmarks(): Promise<RobustnessBenchmarks> {
  return request<RobustnessBenchmarks>('/api/v1/robustness/benchmarks', {
    method: 'GET',
  });
}

// ----------------- Visual Similarity Detection -----------------
export async function compareImagesSimilarity(
  referenceFile: File,
  suspectedFile?: File,
  suspectedUrl?: string
): Promise<SimilarityCompareResult> {
  const formData = new FormData();
  formData.append('reference_file', referenceFile);
  if (suspectedFile) {
    formData.append('suspected_file', suspectedFile);
  }
  if (suspectedUrl) {
    formData.append('suspected_url', suspectedUrl);
  }

  return request<SimilarityCompareResult>('/api/v1/similarity/compare', {
    method: 'POST',
    body: formData,
  });
}

export async function searchVaultSimilarity(
  suspectedFile?: File,
  suspectedUrl?: string,
  token?: string
): Promise<SimilaritySearchResult> {
  const formData = new FormData();
  if (suspectedFile) {
    formData.append('suspected_file', suspectedFile);
  }
  if (suspectedUrl) {
    formData.append('suspected_url', suspectedUrl);
  }

  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return request<SimilaritySearchResult>('/api/v1/similarity/search', {
    method: 'POST',
    headers,
    body: formData,
  });
}

// ----------------- Global Case Management -----------------
export interface CreateCaseParams {
  title: string;
  assetId: number;
  suspectedUrl?: string;
  suspectedCountry?: string;
  matchScore?: number;
  watermarkStatus?: string;
  evidenceNotes?: string;
  suspectedFile?: File;
}

export async function createCase(
  params: CreateCaseParams,
  token: string
): Promise<GlobalCase> {
  const formData = new FormData();
  formData.append('title', params.title);
  formData.append('asset_id', params.assetId.toString());
  if (params.suspectedUrl) formData.append('suspected_url', params.suspectedUrl);
  if (params.suspectedCountry) formData.append('suspected_country', params.suspectedCountry);
  if (params.matchScore !== undefined) formData.append('match_score', params.matchScore.toString());
  if (params.watermarkStatus) formData.append('watermark_status', params.watermarkStatus);
  if (params.evidenceNotes) formData.append('evidence_notes', params.evidenceNotes);
  if (params.suspectedFile) formData.append('suspected_file', params.suspectedFile);

  return request<GlobalCase>('/api/v1/cases', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
}

export async function listCases(
  token: string,
  status?: string,
  country?: string,
  skip = 0,
  limit = 50
): Promise<GlobalCase[]> {
  const params = new URLSearchParams();
  params.append('skip', skip.toString());
  params.append('limit', limit.toString());
  if (status && status !== 'All') params.append('status', status);
  if (country && country !== 'All') params.append('country', country);

  return request<GlobalCase[]>(`/api/v1/cases?${params.toString()}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getCaseDetail(
  caseId: string,
  token: string
): Promise<GlobalCase> {
  return request<GlobalCase>(`/api/v1/cases/${caseId}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateCaseStatus(
  caseId: string,
  status: CaseStatus,
  note: string | undefined,
  token: string
): Promise<GlobalCase> {
  return request<GlobalCase>(`/api/v1/cases/${caseId}/status`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ status, note }),
  });
}

export async function addCaseNote(
  caseId: string,
  note: string,
  token: string
): Promise<GlobalCase> {
  return request<GlobalCase>(`/api/v1/cases/${caseId}/notes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ note }),
  });
}

export async function getCaseReport(
  caseId: string,
  token: string
): Promise<CaseReport> {
  return request<CaseReport>(`/api/v1/cases/${caseId}/report`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
}
