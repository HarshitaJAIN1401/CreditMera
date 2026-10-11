export type SupportedLanguage = 'en' | 'hi' | 'es' | 'fr' | 'de' | 'ja' | 'ar';

export type AssetCategory =
  | 'Wildlife'
  | 'Nature'
  | 'Travel'
  | 'Landscape'
  | 'Portrait'
  | 'Fashion'
  | 'Food'
  | 'Product'
  | 'Architecture'
  | 'Documentary'
  | 'Other';

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Receipt {
  receipt_number: string;
  asset_id: number;
  issued_at: string;
  issuer: string;
  original_file_sha256: string;
  watermarked_file_sha256: string;
  algorithm_version: string;
  payload_version: string;
  owner_declaration_summary: string;
  legal_disclaimer: string;
  receipt_signature: string;
  receipt_payload: Record<string, any>;
}

export interface ImageMetrics {
  psnr_db?: number;
  ssim?: number;
  mse?: number;
  nc?: number;
  ber?: number;
  [key: string]: any;
}

export interface AssetRegistrationResponse {
  asset_id: number;
  registered_asset_id: string;
  title: string;
  original_filename: string;
  original_file_hash: string;
  watermarked_file_hash: string;
  image_width: number;
  image_height: number;
  algorithm: string;
  algorithm_version: string;
  payload_version: string;
  alpha: number;
  registered_at: string;
  receipt: Receipt;
  metrics: ImageMetrics;
  category?: string;
  country?: string;
  license_type?: string;
  attribution_text?: string | null;
  perceptual_hash?: string | null;
}

export interface AssetSummary {
  asset_id: number;
  registered_asset_id: string;
  title: string;
  original_filename: string;
  original_file_hash: string;
  watermarked_file_hash: string;
  image_width: number;
  image_height: number;
  algorithm: string;
  registered_at: string;
  status: string;
  category?: string;
  country?: string;
  license_type?: string;
  attribution_text?: string | null;
  perceptual_hash?: string | null;
}

export interface AssetDetail extends AssetSummary {
  owner_id: string;
  owner_name?: string | null;
  original_file_size: number;
  original_mime_type: string;
  watermarked_file_size: number;
  storage_path_watermarked: string;
  algorithm_version: string;
  payload_version: string;
  alpha: number;
  ownership_declaration: string;
  ownership_declared_at: string;
  metrics?: ImageMetrics | null;
  receipt?: Receipt | null;
}

export type VerificationOutcome =
  | 'MATCHED'
  | 'NOT_DETECTED'
  | 'INVALID_WATERMARK'
  | 'NO_REGISTERED_RECORD'
  | 'INCONCLUSIVE';

export type FileIntegrityState =
  | 'UNMODIFIED_COPY'
  | 'MODIFIED_RE_ENCODED'
  | 'HASH_MISMATCH'
  | 'NOT_APPLICABLE';

export type ReceiptValidationStatus =
  | 'VALID'
  | 'INVALID_SIGNATURE'
  | 'PAYLOAD_MISMATCH'
  | 'NOT_PROVIDED';

export interface VerificationResponse {
  outcome: VerificationOutcome;
  explanation: string;
  file_integrity: FileIntegrityState;
  extracted_asset_id: number | null;
  candidate_header_detected: boolean;
  crc_valid: boolean;
  hmac_valid: boolean;
  normalized_cross_correlation: number | null;
  bit_error_rate: number | null;
  matched_asset_title: string | null;
  registered_at: string | null;
  owner_declaration_summary: string | null;
  is_owner: boolean | null;
  receipt_validation_status: ReceiptValidationStatus | null;
  diagnostics: Record<string, any>;
}

export interface ReceiptVerifyResponse {
  signature_valid: boolean;
  database_match: boolean;
  details: string;
  receipt_number: string | null;
  asset_id: number | null;
  registered_title: string | null;
  registered_at: string | null;
  issuer: string | null;
}

export interface RobustnessMetadata {
  title: string;
  timestamp: string;
  smoke_test: boolean;
  algorithms_evaluated: string[];
  images_evaluated: string[];
  total_watermarked_trials: number;
  total_control_trials: number;
  false_positives_detected: number;
  false_positive_rate: number;
  default_alpha: number;
  asset_id: number;
}

export interface AlgorithmMetricsSummary {
  total_samples: number;
  authenticated_count: number;
  authentication_rate: number;
  mean_nc: number;
  mean_ber: number;
  mean_psnr_db: number;
  mean_ssim: number;
}

export interface AttackMetricsSummary {
  total_samples: number;
  authenticated_count: number;
  authentication_rate: number;
  mean_nc: number;
  mean_ber: number;
  mean_psnr_db: number;
  mean_ssim: number;
  description?: string;
}

export interface RobustnessBenchmarks {
  metadata: RobustnessMetadata;
  summary_by_algorithm: Record<string, AlgorithmMetricsSummary>;
  summary_by_attack: Record<string, AttackMetricsSummary>;
  samples?: any[];
}

export interface AsyncJobStatus {
  job_id: string;
  user_id: string;
  job_type: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress: number;
  title?: string | null;
  asset_id?: number | null;
  result?: Record<string, any> | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface AsyncJobSubmission {
  job_id: string;
  status: string;
  job_type: string;
  poll_url: string;
  message: string;
}

export interface AsyncJobListResponse {
  jobs: AsyncJobStatus[];
  total: number;
  skip: number;
  limit: number;
}

// ----------------- Global Case Management Types -----------------
export type CaseStatus =
  | 'New'
  | 'Potential Match'
  | 'Evidence Collected'
  | 'Contacted'
  | 'Under Review'
  | 'Resolved'
  | 'Closed';

export interface CaseTimelineItem {
  timestamp: string;
  action: string;
  actor: string;
  details?: string;
}

export interface GlobalCase {
  id: string;
  case_number: string;
  asset_id: number;
  asset_title: string;
  title: string;
  suspected_image_path?: string | null;
  suspected_url?: string | null;
  suspected_country?: string | null;
  match_score?: number | null;
  watermark_status?: string | null;
  status: CaseStatus;
  evidence_notes?: string | null;
  timeline: CaseTimelineItem[];
  created_at: string;
  updated_at: string;
}

export interface CaseReport {
  report_id: string;
  generated_at: string;
  case: GlobalCase;
  registered_asset_metadata: Record<string, any>;
  technical_evidence_summary: Record<string, any>;
  disclaimer: string;
}

// ----------------- Visual Similarity Types -----------------
export interface SimilarityCompareResult {
  composite_similarity_score: number;
  similarity_percentage: number;
  similarity_tier: string;
  explanation: string;
  metrics: {
    phash: {
      hash_a: string;
      hash_b: string;
      hamming_distance: number;
      similarity_score: number;
    };
    dhash: {
      hash_a: string;
      hash_b: string;
      hamming_distance: number;
      similarity_score: number;
    };
    ssim: {
      score: number;
    };
  };
  dimensions: {
    image_a: [number, number];
    image_b: [number, number];
  };
  legal_disclaimer: string;
}

export interface SimilaritySearchMatch {
  asset_id: number;
  title: string;
  category: string;
  country: string;
  hamming_distance: number;
  similarity_score: number;
  similarity_percentage: number;
  similarity_tier: string;
}

export interface SimilaritySearchResult {
  query_phash: string;
  total_registered_evaluated: number;
  matches: SimilaritySearchMatch[];
  top_match?: SimilaritySearchMatch | null;
  legal_disclaimer: string;
}
