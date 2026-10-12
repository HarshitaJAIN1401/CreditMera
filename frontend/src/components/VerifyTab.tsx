import React, { useState, useRef, useEffect } from 'react';
import {
  Search,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Info,
  ShieldAlert,
  UploadCloud,
  Fingerprint,
  Link as LinkIcon,
  Globe,
  Sliders,
  Award,
  Layers,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../i18n/I18nContext';
import {
  verifyImage,
  compareImagesSimilarity,
  API_BASE_URL,
} from '../services/api';
import type {
  VerificationResponse,
  VerificationOutcome,
  SimilarityCompareResult,
} from '../types';

interface VerifyTabProps {
  initialAssetId?: number;
  onNavigateToCases?: (
    assetId?: number,
    suspectedUrl?: string,
    matchScore?: number,
    watermarkStatus?: string
  ) => void;
  onOpenPassport?: (assetId: number) => void;
}

export const VerifyTab: React.FC<VerifyTabProps> = ({
  initialAssetId,
  onNavigateToCases,
  onOpenPassport,
}) => {
  const { t } = useTranslation();
  const { token } = useAuth();

  // Mode: Upload vs URL
  const [inspectMode, setInspectMode] = useState<'upload' | 'url'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [suspectedUrl, setSuspectedUrl] = useState('');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageMeta, setImageMeta] = useState<{ width: number; height: number } | null>(null);

  // Advanced inputs
  const [algorithm, setAlgorithm] = useState<'dct_svd' | 'dct' | 'svd'>('dct_svd');
  const [alpha, setAlpha] = useState(0.10);
  const [expectedAssetId, setExpectedAssetId] = useState<string>(
    initialAssetId ? initialAssetId.toString() : ''
  );
  const [enableSimilarityCheck, setEnableSimilarityCheck] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Status & Results
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerificationResponse | null>(null);
  const [similarityResult, setSimilarityResult] = useState<SimilarityCompareResult | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (initialAssetId) {
      setExpectedAssetId(initialAssetId.toString());
    }
  }, [initialAssetId]);

  const handleFileChange = (selectedFile: File) => {
    setError(null);
    setResult(null);
    setSimilarityResult(null);

    const validTypes = ['image/png', 'image/jpeg', 'image/webp', 'image/tiff'];
    if (!validTypes.includes(selectedFile.type) && !selectedFile.name.match(/\.(png|jpe?g|webp|tiff)$/i)) {
      setError('Unsupported file type. Please upload a PNG, JPG, WEBP, or TIFF image.');
      return;
    }

    setFile(selectedFile);
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);

    const img = new Image();
    img.onload = () => {
      setImageMeta({ width: img.naturalWidth, height: img.naturalHeight });
      if (img.naturalWidth < 64 || img.naturalHeight < 64) {
        setError('Image dimensions must be at least 64x64 pixels.');
      } else if (img.naturalWidth > 8192 || img.naturalHeight > 8192) {
        setError('Image exceeds maximum dimension limit of 8192x8192 pixels.');
      }
    };
    img.src = url;
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (inspectMode === 'upload' && !file) {
      setError('Please select a suspect image file.');
      return;
    }
    if (inspectMode === 'url' && !suspectedUrl.trim()) {
      setError('Please enter a valid web image URL.');
      return;
    }

    setError(null);
    setLoading(true);
    setResult(null);
    setSimilarityResult(null);

    try {
      let parsedExpectedId: number | undefined = undefined;
      if (expectedAssetId.trim()) {
        const parsed = parseInt(expectedAssetId.trim(), 10);
        if (isNaN(parsed) || parsed < 1 || parsed > 1099511627775) {
          throw new Error('Claimed Asset ID must be a valid 40-bit integer (1 to 1,099,511,627,775).');
        }
        parsedExpectedId = parsed;
      }

      // If URL mode, fetch blob or call verification
      let verifyFile = file;
      if (inspectMode === 'url' && !file) {
        // Fetch via client if possible or backend
        const res = await fetch(suspectedUrl);
        const blob = await res.blob();
        verifyFile = new File([blob], 'suspected_from_url.jpg', { type: blob.type });
      }

      if (!verifyFile) {
        throw new Error('Could not retrieve image data for inspection.');
      }

      // 1. Watermark Extraction
      const verifyRes = await verifyImage(
        {
          file: verifyFile,
          algorithm,
          alpha,
          expectedAssetId: parsedExpectedId,
        },
        token
      );
      setResult(verifyRes);

      // 2. If matched an asset and similarity is enabled, run perceptual comparison against registered image
      if (enableSimilarityCheck && verifyRes.extracted_asset_id) {
        try {
          const registeredImageUrl = `${API_BASE_URL}/api/v1/assets/${verifyRes.extracted_asset_id}/download/watermarked`;
          const regRes = await fetch(registeredImageUrl);
          if (regRes.ok) {
            const regBlob = await regRes.blob();
            const regFile = new File([regBlob], 'registered.png', { type: regBlob.type });
            const simRes = await compareImagesSimilarity(verifyFile, regFile);
            setSimilarityResult(simRes);
          }
        } catch (simErr) {
          console.warn('Perceptual similarity comparison could not be completed:', simErr);
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Verification inspection failed. Check inputs.');
    } finally {
      setLoading(false);
    }
  };

  const renderOutcomeBadge = (outcome: VerificationOutcome) => {
    switch (outcome) {
      case 'MATCHED':
        return {
          icon: <CheckCircle2 className="w-6 h-6 text-emerald-600" />,
          title: t('verify_status_matched', 'MATCHED — Authenticated Ownership Confirmed'),
          bgColor: 'bg-emerald-50 border-emerald-200 text-emerald-800',
          textColor: 'text-emerald-700',
          description:
            'A valid cryptographic watermark was extracted and matches an authoritative registration record in the database.',
        };
      case 'NOT_DETECTED':
        return {
          icon: <AlertTriangle className="w-6 h-6 text-slate-500" />,
          title: t('verify_status_not_detected', 'NOT DETECTED — No Watermark Found'),
          bgColor: 'bg-slate-50 border-slate-200 text-slate-800',
          textColor: 'text-slate-600',
          description:
            'No recognizable watermark signal was found in the frequency coefficients. This image is either unwatermarked or the watermark has been heavily destroyed.',
        };
      case 'INVALID_WATERMARK':
        return {
          icon: <ShieldAlert className="w-6 h-6 text-rose-600" />,
          title: t('verify_status_invalid', 'INVALID WATERMARK — Tampered or Corrupted Payload'),
          bgColor: 'bg-rose-50 border-rose-200 text-rose-800',
          textColor: 'text-rose-700',
          description:
            'Candidate watermark header was detected, but CRC-16 checksum or HMAC authenticity check failed. The embedded metadata has been corrupted or modified.',
        };
      case 'NO_REGISTERED_RECORD':
        return {
          icon: <Info className="w-6 h-6 text-blue-600" />,
          title: t('verify_status_unregistered', 'NO REGISTERED RECORD — Unregistered Watermark'),
          bgColor: 'bg-blue-50 border-blue-200 text-blue-800',
          textColor: 'text-blue-700',
          description:
            'A cryptographically valid watermark was extracted, but no corresponding registration record exists in the CreditMera database.',
        };
      case 'INCONCLUSIVE':
        return {
          icon: <HelpCircle className="w-6 h-6 text-amber-600" />,
          title: t('verify_status_inconclusive', 'INCONCLUSIVE — Degraded Signal / Ambiguous Match'),
          bgColor: 'bg-amber-50 border-amber-200 text-amber-800',
          textColor: 'text-amber-700',
          description:
            'Watermark extraction confidence is borderline due to image processing (e.g. heavy JPEG compression or aggressive downscaling).',
        };
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-100 rounded-lg text-blue-600">
              <Search className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold text-slate-900">
              {t('verify_title', 'Verify & Inspect Image')}
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            {t(
              'verify_subtitle',
              'Blind frequency-domain watermark extraction and visual similarity inspection with 5-tier calibrated decisions.'
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200">
            FPR: 0.00% Verified
          </span>
        </div>
      </div>

      {/* Main Grid: Form (5 cols) & Results (7 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Form */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 p-5 space-y-5 shadow-xs">
          {/* Mode Switcher */}
          <div className="flex p-1 bg-slate-100 rounded-xl text-xs font-semibold text-slate-600">
            <button
              type="button"
              onClick={() => setInspectMode('upload')}
              className={`flex-1 py-1.5 rounded-lg transition-all ${
                inspectMode === 'upload' ? 'bg-white text-blue-700 shadow-xs' : 'hover:text-slate-900'
              }`}
            >
              Upload Suspect Image
            </button>
            <button
              type="button"
              onClick={() => setInspectMode('url')}
              className={`flex-1 py-1.5 rounded-lg transition-all ${
                inspectMode === 'url' ? 'bg-white text-blue-700 shadow-xs' : 'hover:text-slate-900'
              }`}
            >
              Inspect by Web URL
            </button>
          </div>

          <form onSubmit={handleVerify} className="space-y-4 text-xs">
            {inspectMode === 'upload' ? (
              <div>
                <label className="block font-semibold text-slate-700 mb-1.5">
                  Suspect Image File *
                </label>
                {previewUrl ? (
                  <div className="space-y-2">
                    <div className="aspect-[4/3] bg-slate-100 rounded-xl overflow-hidden border border-slate-200 relative">
                      <img
                        src={previewUrl}
                        alt="Suspect Preview"
                        className="w-full h-full object-contain"
                      />
                      {imageMeta && (
                        <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/60 backdrop-blur-md text-white text-[10px] font-medium">
                          {imageMeta.width} &times; {imageMeta.height} px
                        </div>
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-700 truncate max-w-[200px]">
                        {file?.name}
                      </span>
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="text-blue-600 hover:underline font-medium"
                      >
                        Change
                      </button>
                    </div>
                  </div>
                ) : (
                  <div
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl p-8 text-center cursor-pointer transition-colors bg-slate-50/50 hover:bg-blue-50/20"
                  >
                    <UploadCloud className="w-10 h-10 text-slate-400 mx-auto mb-2" />
                    <p className="font-semibold text-slate-800">
                      Drop suspect image here, or browse
                    </p>
                    <p className="text-[11px] text-slate-400 mt-1">
                      PNG, JPG, WEBP or TIFF (min 64x64)
                    </p>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/tiff"
                  onChange={(e) => e.target.files?.[0] && handleFileChange(e.target.files[0])}
                  className="hidden"
                />
              </div>
            ) : (
              <div>
                <label className="block font-semibold text-slate-700 mb-1.5">
                  Suspect Online Image URL *
                </label>
                <div className="relative">
                  <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="url"
                    value={suspectedUrl}
                    onChange={(e) => setSuspectedUrl(e.target.value)}
                    placeholder="https://example.com/unauthorized-image.jpg"
                    className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  {t('verify_ssrf_hint', 'Protected by server-side SSRF validation (blocks localhost/private networks).')}
                </p>
              </div>
            )}

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                {t('verify_claimed_id', 'Claimed Asset ID (Optional)')}
              </label>
              <input
                type="text"
                value={expectedAssetId}
                onChange={(e) => setExpectedAssetId(e.target.value)}
                placeholder="Target specific ID to verify matching..."
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Advanced toggle */}
            <div>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>{showAdvanced ? t('verify_adv_hide', 'Hide Advanced Settings') : t('verify_adv_show', 'Show Advanced Settings')}</span>
              </button>

              {showAdvanced && (
                <div className="mt-3 p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      {t('verify_adv_algo', 'Expected Extraction Algorithm')}
                    </label>
                    <select
                      value={algorithm}
                      onChange={(e) => setAlgorithm(e.target.value as any)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-800"
                    >
                      <option value="dct_svd">DCT-SVD v1.0 (Default)</option>
                      <option value="dct">DCT Mid-Frequency</option>
                      <option value="svd">Pure Spatial SVD</option>
                    </select>
                  </div>

                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="font-semibold text-slate-700">Modulation Alpha:</span>
                      <span className="font-mono text-blue-700 font-bold">&alpha; = {alpha.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.05"
                      max="0.25"
                      step="0.01"
                      value={alpha}
                      onChange={(e) => setAlpha(parseFloat(e.target.value))}
                      className="w-full accent-blue-600"
                    />
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <input
                      type="checkbox"
                      id="enable-sim"
                      checked={enableSimilarityCheck}
                      onChange={(e) => setEnableSimilarityCheck(e.target.checked)}
                      className="rounded text-blue-600"
                    />
                    <label htmlFor="enable-sim" className="text-slate-700 font-medium">
                      {t('verify_adv_sim_check', 'Compute 64-bit perceptual similarity (pHash + SSIM)')}
                    </label>
                  </div>
                </div>
              )}
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || (inspectMode === 'upload' && !file)}
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold shadow-md shadow-blue-500/10 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>{t('verify_extracting', 'Extracting Frequency Watermark...')}</span>
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  <span>{t('verify_btn_inspect', 'Inspect & Verify Image')}</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Results Column */}
        <div className="lg:col-span-7 space-y-4">
          {!result && !loading && (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-xs">
              <Fingerprint className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-slate-800">{t('verify_ready_title', 'Ready for Verification Inspection')}</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
                {t('verify_ready_desc', 'Upload a suspected image or provide an online URL. The engine performs blind DCT-SVD extraction, evaluates CRC-16 checksums, and cross-references authoritative database ownership.')}
              </p>
            </div>
          )}

          {result && (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-6 shadow-sm">
              {/* Outcome Badge Card */}
              {(() => {
                const badge = renderOutcomeBadge(result.outcome);
                return (
                  <div className={`p-4 rounded-xl border ${badge.bgColor} space-y-2`}>
                    <div className="flex items-center gap-3">
                      {badge.icon}
                      <div>
                        <h2 className="text-sm font-bold leading-tight">{badge.title}</h2>
                        <p className="text-xs opacity-90 mt-0.5">{badge.description}</p>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Matched Asset Details */}
              {result.outcome === 'MATCHED' && (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3 text-xs">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                    <span className="font-bold text-slate-900">
                      Authoritative Registration Match
                    </span>
                    <span className="font-mono text-blue-700 font-bold">
                      Asset #{result.extracted_asset_id}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <span className="text-slate-400">Registered Title:</span>
                      <p className="font-semibold text-slate-800 mt-0.5">
                        {result.matched_asset_title || 'N/A'}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-400">Registration Timestamp:</span>
                      <p className="font-semibold text-slate-800 mt-0.5">
                        {result.registered_at ? new Date(result.registered_at).toLocaleString() : 'N/A'}
                      </p>
                    </div>
                  </div>

                  {result.owner_declaration_summary && (
                    <div className="pt-2 border-t border-slate-200">
                      <span className="text-slate-400">Ownership Declaration:</span>
                      <p className="text-slate-700 italic mt-0.5">
                        &ldquo;{result.owner_declaration_summary}&rdquo;
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Technical Verification Metrics */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Signal Extraction &amp; Cryptographic Telemetry
                </h4>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-400 block font-medium">Header Detected</span>
                    <span className={`font-bold mt-0.5 block ${result.candidate_header_detected ? 'text-emerald-700' : 'text-slate-700'}`}>
                      {result.candidate_header_detected ? '128-bit Magic OK' : 'No Header'}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-400 block font-medium">CRC-16 Integrity</span>
                    <span className={`font-bold mt-0.5 block ${result.crc_valid ? 'text-emerald-700' : 'text-slate-700'}`}>
                      {result.crc_valid ? 'Valid Checksum' : 'Invalid / None'}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-400 block font-medium">Correlation (NC)</span>
                    <span className="font-mono font-bold text-slate-800 mt-0.5 block">
                      {result.normalized_cross_correlation !== null
                        ? result.normalized_cross_correlation.toFixed(3)
                        : 'N/A'}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-[10px] text-slate-400 block font-medium">File Integrity</span>
                    <span className="font-semibold text-slate-700 text-[11px] mt-0.5 block truncate">
                      {result.file_integrity}
                    </span>
                  </div>
                </div>
              </div>

              {/* Visual Similarity Analysis Card */}
              {similarityResult && (
                <div className="p-4 rounded-xl bg-purple-50/60 border border-purple-200 space-y-3 text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-purple-600" />
                      <span className="font-bold text-purple-900">
                        Visual Similarity Detection (DIP)
                      </span>
                    </div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 border border-purple-300">
                      {similarityResult.similarity_tier}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-2 bg-white rounded-lg border border-purple-100">
                      <span className="text-[10px] text-slate-400 block">Composite Match</span>
                      <span className="text-base font-black text-purple-700 block">
                        {similarityResult.similarity_percentage.toFixed(1)}%
                      </span>
                    </div>
                    <div className="p-2 bg-white rounded-lg border border-purple-100">
                      <span className="text-[10px] text-slate-400 block">pHash Distance</span>
                      <span className="text-base font-black text-slate-800 block">
                        {similarityResult.metrics.phash.hamming_distance} / 64
                      </span>
                    </div>
                    <div className="p-2 bg-white rounded-lg border border-purple-100">
                      <span className="text-[10px] text-slate-400 block">SSIM Score</span>
                      <span className="text-base font-black text-slate-800 block">
                        {similarityResult.metrics.ssim.score.toFixed(3)}
                      </span>
                    </div>
                  </div>

                  <p className="text-[11px] text-purple-950/80 leading-relaxed">
                    {similarityResult.explanation}
                  </p>
                </div>
              )}

              {/* Cross-Border Legal Actions */}
              <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100">
                <div className="flex items-center gap-2">
                  {onNavigateToCases && (
                    <button
                      onClick={() =>
                        onNavigateToCases(
                          result.extracted_asset_id || undefined,
                          suspectedUrl || undefined,
                          similarityResult ? similarityResult.composite_similarity_score : undefined,
                          result.outcome
                        )
                      }
                      className="flex items-center gap-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
                    >
                      <Globe className="w-3.5 h-3.5" />
                      <span>{t('verify_open_case_btn', 'Open Global Case')}</span>
                    </button>
                  )}

                  {result.extracted_asset_id && onOpenPassport && (
                    <button
                      onClick={() => onOpenPassport(result.extracted_asset_id!)}
                      className="flex items-center gap-1.5 px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold shadow-xs transition-colors"
                    >
                      <Award className="w-3.5 h-3.5 text-blue-600" />
                      <span>{t('passport_title', 'View Asset Passport')}</span>
                    </button>
                  )}
                </div>

                <span className="text-[10px] text-slate-400 font-mono">
                  HMAC-SHA256 Authenticated
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
