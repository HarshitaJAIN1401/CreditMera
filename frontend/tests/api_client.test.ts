import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  registerUser,
  loginUser,
  getCurrentUser,
  registerAsset,
  registerAssetAsync,
  getJobStatus,
  listJobs,
  downloadWatermarkedImage,
  listAssets,
  getAssetDetail,
  getReceipt,
  verifyImage,
  verifyReceiptRecord,
  fetchRobustnessBenchmarks,
} from '../src/services/api';

describe('CreditMera Frontend API Client Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('registerUser sends POST to /api/v1/auth/register with user JSON payload', async () => {
    const mockUser = {
      id: 'uuid-123',
      email: 'creator@creditmera.org',
      full_name: 'Test Creator',
      is_active: true,
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockUser,
    } as Response);

    const result = await registerUser('creator@creditmera.org', 'securepassword123', 'Test Creator');
    expect(result).toEqual(mockUser);
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/auth/register',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          email: 'creator@creditmera.org',
          password: 'securepassword123',
          full_name: 'Test Creator',
        }),
      })
    );
  });

  it('loginUser sends POST to /api/v1/auth/login and receives access token', async () => {
    const mockToken = {
      access_token: 'jwt-bearer-token-xyz',
      token_type: 'bearer',
      user: {
        id: 'uuid-123',
        email: 'creator@creditmera.org',
        full_name: 'Test Creator',
        is_active: true,
      },
    };

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockToken,
    } as Response);

    const result = await loginUser('creator@creditmera.org', 'securepassword123');
    expect(result.access_token).toBe('jwt-bearer-token-xyz');
  });

  it('getCurrentUser sends GET to /api/v1/auth/me with Bearer token', async () => {
    const mockUser = {
      id: 'uuid-123',
      email: 'creator@creditmera.org',
      full_name: 'Test Creator',
      is_active: true,
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockUser,
    } as Response);

    const result = await getCurrentUser('mock-token-xyz');
    expect(result).toEqual(mockUser);
    const headers = fetchSpy.mock.calls[0][1]?.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer mock-token-xyz');
  });

  it('listAssets formats pagination query params skip and limit', async () => {
    const mockList = [
      {
        asset_id: 1020304050,
        registered_asset_id: 'uuid-asset-1',
        title: 'Horizon Pavilion',
        original_filename: 'horizon.png',
        original_file_hash: 'sha-orig',
        watermarked_file_hash: 'sha-wm',
        image_width: 512,
        image_height: 512,
        algorithm: 'dct_svd',
        registered_at: '2026-10-10T12:00:00Z',
        status: 'ACTIVE',
      },
    ];

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockList,
    } as Response);

    const result = await listAssets('mock-token-xyz', 10, 25);
    expect(result).toHaveLength(1);
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/assets?skip=10&limit=25',
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('verifyImage sends multipart FormData and parses VerificationResponse', async () => {
    const mockVerifyResponse = {
      outcome: 'MATCHED',
      explanation: 'Watermark verified against registered database record.',
      file_integrity: 'UNMODIFIED_COPY',
      extracted_asset_id: 1020304050,
      candidate_header_detected: true,
      crc_valid: true,
      hmac_valid: true,
      normalized_cross_correlation: 1.0,
      bit_error_rate: 0.0,
      matched_asset_title: 'Horizon Pavilion',
      registered_at: '2026-10-10T12:00:00Z',
      owner_declaration_summary: 'Sole author.',
      is_owner: true,
      receipt_validation_status: 'VALID',
      diagnostics: {},
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockVerifyResponse,
    } as Response);

    const file = new File(['fake-png-content'], 'suspect.png', { type: 'image/png' });
    const result = await verifyImage(
      {
        file,
        algorithm: 'dct_svd',
        alpha: 0.1,
        expectedAssetId: 1020304050,
      },
      'bearer-token-123'
    );

    expect(result.outcome).toBe('MATCHED');
    expect(result.extracted_asset_id).toBe(1020304050);
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/verify',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('verifyReceiptRecord sends JSON payload to /api/v1/assets/receipts/verify', async () => {
    const mockReceiptResponse = {
      signature_valid: true,
      database_match: true,
      details: 'HMAC signature authentic and matches registered record.',
      receipt_number: 'CRMR-REC-001',
      asset_id: 1020304050,
      registered_title: 'Horizon Pavilion',
      registered_at: '2026-10-10T12:00:00Z',
      issuer: 'CreditMera Ownership Authority v1.0',
    };

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockReceiptResponse,
    } as Response);

    const payload = { asset_id: 1020304050, issuer: 'CreditMera' };
    const result = await verifyReceiptRecord(payload, 'signature-hex-123');
    expect(result.signature_valid).toBe(true);
    expect(result.database_match).toBe(true);
  });

  it('fetchRobustnessBenchmarks retrieves benchmarks endpoint', async () => {
    const mockBenchmarks = {
      metadata: {
        title: 'CreditMera Watermark Robustness Lab Evaluation',
        timestamp: '2026-10-10T21:09:23Z',
        smoke_test: false,
        algorithms_evaluated: ['dct_svd', 'dct', 'svd'],
        images_evaluated: ['texture_256'],
        total_watermarked_trials: 336,
        total_control_trials: 12,
        false_positives_detected: 0,
        false_positive_rate: 0.0,
        default_alpha: 0.1,
        asset_id: 1020304050,
      },
      summary_by_algorithm: {
        dct_svd: {
          total_samples: 112,
          authenticated_count: 29,
          authentication_rate: 0.2589,
          mean_nc: 0.4063,
          mean_ber: 0.2969,
          mean_psnr_db: 33.0,
          mean_ssim: 0.8353,
        },
      },
      summary_by_attack: {},
    };

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockBenchmarks,
    } as Response);

    const result = await fetchRobustnessBenchmarks();
    expect(result.metadata.false_positive_rate).toBe(0.0);
    expect(result.summary_by_algorithm.dct_svd.mean_nc).toBe(0.4063);
  });

  it('handles backend error detail cleanly', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ detail: 'Image dimensions must be at least 64x64' }),
    } as Response);

    await expect(
      registerAsset(
        {
          file: new File([''], 'tiny.png'),
          title: 'Tiny',
          ownershipDeclaration: 'Legal owner statement declaration.',
          algorithm: 'dct_svd',
          alpha: 0.1,
        },
        'token'
      )
    ).rejects.toThrow('Image dimensions must be at least 64x64');
  });

  it('registerAssetAsync sends multipart POST to /api/v1/assets/register-async', async () => {
    const mockResponse = {
      job_id: 'job-uuid-456',
      status: 'PENDING',
      job_type: 'ASSET_REGISTRATION',
      poll_url: '/api/v1/jobs/job-uuid-456',
      message: 'Asset registration accepted for background processing.',
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockResponse,
    } as Response);

    const result = await registerAssetAsync(
      {
        file: new File(['fake-png-bytes'], 'artwork.png', { type: 'image/png' }),
        title: 'Asynchronous Artwork',
        ownershipDeclaration: 'Ownership declaration assertion statement.',
        algorithm: 'dct_svd',
        alpha: 0.12,
        idempotencyKey: 'idem-uuid-789',
      },
      'bearer-token'
    );

    expect(result.job_id).toBe('job-uuid-456');
    expect(result.status).toBe('PENDING');
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/assets/register-async',
      expect.objectContaining({
        method: 'POST',
      })
    );
  });

  it('getJobStatus sends GET to /api/v1/jobs/:job_id', async () => {
    const mockJob = {
      job_id: 'job-uuid-456',
      user_id: 'user-123',
      job_type: 'ASSET_REGISTRATION',
      status: 'COMPLETED',
      progress: 100,
      title: 'Asynchronous Artwork',
      asset_id: 10001,
      result: { asset_id: 10001 },
      error_message: null,
      created_at: '2026-10-10T22:00:00Z',
      updated_at: '2026-10-10T22:00:05Z',
      completed_at: '2026-10-10T22:00:05Z',
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockJob,
    } as Response);

    const result = await getJobStatus('job-uuid-456', 'bearer-token');
    expect(result.status).toBe('COMPLETED');
    expect(result.progress).toBe(100);
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/jobs/job-uuid-456',
      expect.objectContaining({
        method: 'GET',
      })
    );
  });

  it('listJobs sends GET to /api/v1/jobs with skip and limit params', async () => {
    const mockList = {
      jobs: [],
      total: 0,
      skip: 10,
      limit: 20,
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockList,
    } as Response);

    const result = await listJobs('bearer-token', 10, 20);
    expect(result.total).toBe(0);
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/jobs?skip=10&limit=20',
      expect.objectContaining({
        method: 'GET',
      })
    );
  });

  it('downloadWatermarkedImage appends presigned=true when requested', async () => {
    const mockBlob = new Blob(['image-bytes'], { type: 'image/png' });
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'image/png' }),
      blob: async () => mockBlob,
    } as Response);

    await downloadWatermarkedImage('bearer-token', 4001, true);
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/assets/4001/download/watermarked?presigned=true',
      expect.objectContaining({
        method: 'GET',
      })
    );
  });
});
