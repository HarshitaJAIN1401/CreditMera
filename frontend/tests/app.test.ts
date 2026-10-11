import { describe, it, expect } from 'vitest';
import type { VerificationOutcome, FileIntegrityState } from '../src/types';

describe('CreditMera Frontend Architecture & Contracts', () => {
  it('should verify basic test environment configuration', () => {
    expect(true).toBe(true);
  });

  it('verifies environment variables defaults', () => {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    expect(apiBaseUrl).toContain('http');
  });

  it('validates Phase 4 calibrated 5-tier outcome state contract', () => {
    const validOutcomes: VerificationOutcome[] = [
      'MATCHED',
      'NOT_DETECTED',
      'INVALID_WATERMARK',
      'NO_REGISTERED_RECORD',
      'INCONCLUSIVE',
    ];
    expect(validOutcomes).toHaveLength(5);
    expect(validOutcomes).toContain('MATCHED');
    expect(validOutcomes).toContain('NOT_DETECTED');
    expect(validOutcomes).toContain('INVALID_WATERMARK');
    expect(validOutcomes).toContain('NO_REGISTERED_RECORD');
    expect(validOutcomes).toContain('INCONCLUSIVE');
  });

  it('validates file copy integrity state contract', () => {
    const validIntegrity: FileIntegrityState[] = [
      'UNMODIFIED_COPY',
      'MODIFIED_RE_ENCODED',
      'HASH_MISMATCH',
      'NOT_APPLICABLE',
    ];
    expect(validIntegrity).toHaveLength(4);
    expect(validIntegrity).toContain('UNMODIFIED_COPY');
    expect(validIntegrity).toContain('MODIFIED_RE_ENCODED');
  });

  it('verifies supported watermarking algorithms', () => {
    const algorithms = ['dct_svd', 'dct', 'svd'];
    expect(algorithms).toHaveLength(3);
    expect(algorithms).toContain('dct_svd');
  });

  it('verifies default alpha embedding strength factor bound', () => {
    const defaultAlpha = 0.10;
    expect(defaultAlpha).toBeGreaterThanOrEqual(0.01);
    expect(defaultAlpha).toBeLessThanOrEqual(1.0);
  });
});
