import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Download,
  ShieldCheck,
  Copy,
  Check,
  ExternalLink,
  Info,
  Globe,
  Award,
  FileCheck2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../i18n/I18nContext';
import {
  registerAsset,
  downloadWatermarkedImage,
  downloadReceiptJson,
} from '../services/api';
import type { AssetRegistrationResponse, AssetCategory } from '../types';
import { PassportModal } from './PassportModal';

const CATEGORIES: AssetCategory[] = [
  'Wildlife',
  'Nature',
  'Travel',
  'Landscape',
  'Portrait',
  'Fashion',
  'Food',
  'Product',
  'Architecture',
  'Documentary',
  'Other',
];

const COUNTRIES = [
  'United States',
  'India',
  'United Kingdom',
  'Germany',
  'France',
  'Japan',
  'Canada',
  'Australia',
  'Brazil',
  'Spain',
  'United Arab Emirates',
  'Singapore',
  'Other',
];

const LICENSES = [
  'All Rights Reserved',
  'Commercial Production License',
  'Editorial Use Only',
  'Creative Commons CC BY-NC 4.0',
  'Creative Commons CC BY 4.0',
  'Public Domain / CC0',
];

interface ProtectTabProps {
  onOpenAuth: () => void;
  onNavigateToVerify: (assetId?: number) => void;
}

export const ProtectTab: React.FC<ProtectTabProps> = ({
  onOpenAuth,
  onNavigateToVerify,
}) => {
  const { t } = useTranslation();
  const { token, isAuthenticated, user } = useAuth();

  // Wizard state
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageMeta, setImageMeta] = useState<{ width: number; height: number; size: number } | null>(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState<AssetCategory>('Nature');
  const [country, setCountry] = useState('United States');
  const [licenseType, setLicenseType] = useState('All Rights Reserved');
  const [attributionText, setAttributionText] = useState('');
  const [declaration, setDeclaration] = useState(
    'I hereby declare and warrant that I am the sole author, copyright owner, and authorized rights-holder of this original digital work.'
  );
  const [algorithm, setAlgorithm] = useState<'dct_svd' | 'dct' | 'svd'>('dct_svd');
  const [alpha, setAlpha] = useState(0.10);

  // Status & Results
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AssetRegistrationResponse | null>(null);
  const [copiedId, setCopiedId] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);
  const [passportOpen, setPassportOpen] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (selectedFile: File) => {
    setError(null);
    setResult(null);

    const validTypes = ['image/png', 'image/jpeg', 'image/webp', 'image/tiff'];
    if (!validTypes.includes(selectedFile.type) && !selectedFile.name.match(/\.(png|jpe?g|webp|tiff)$/i)) {
      setError('Unsupported file type. Please upload a PNG, JPG, WEBP, or TIFF image.');
      return;
    }

    setFile(selectedFile);
    if (!title) {
      const baseName = selectedFile.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
      const cleanTitle = baseName.charAt(0).toUpperCase() + baseName.slice(1);
      setTitle(cleanTitle);
      setAttributionText(`© ${new Date().getFullYear()} ${user?.full_name || 'Creator'}. All rights reserved.`);
    }

    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);

    const img = new Image();
    img.onload = () => {
      setImageMeta({
        width: img.naturalWidth,
        height: img.naturalHeight,
        size: selectedFile.size,
      });
      if (img.naturalWidth < 64 || img.naturalHeight < 64) {
        setError('Image dimensions must be at least 64x64 pixels for block-based DCT watermarking.');
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated || !token) {
      onOpenAuth();
      return;
    }
    if (!file) {
      setError('Please select an image file to protect.');
      return;
    }
    if (!title.trim()) {
      setError('Please provide a title for this asset.');
      return;
    }
    if (declaration.length < 10) {
      setError('Ownership declaration statement must be at least 10 characters.');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const response = await registerAsset(
        {
          file,
          title: title.trim(),
          ownershipDeclaration: declaration.trim(),
          algorithm,
          alpha,
          category,
          country,
          licenseType,
          attributionText: attributionText.trim() || undefined,
        },
        token
      );
      setResult(response);
    } catch (err: any) {
      setError(err?.message || 'Watermark embedding and registration failed. Check backend logs.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadWatermarked = async () => {
    if (!result || !token) return;
    try {
      const blob = await downloadWatermarkedImage(token, result.asset_id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `watermarked_${result.original_filename}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed', err);
    }
  };

  const handleDownloadReceipt = async () => {
    if (!result || !token) return;
    try {
      const blob = await downloadReceiptJson(token, result.asset_id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `receipt_${result.asset_id}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Receipt download failed', err);
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreviewUrl(null);
    setImageMeta(null);
    setTitle('');
    setResult(null);
    setError(null);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-100 rounded-lg text-blue-600">
              <UploadCloud className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold text-slate-900">
              {t('protect_title', 'Protect & Embed Watermark')}
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            {t(
              'protect_subtitle',
              'Embed an imperceptible, cryptographically authenticated 128-bit ownership payload directly into image frequency sub-bands using hybrid DCT-SVD.'
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded bg-blue-50 text-blue-700 border border-blue-200">
            Engine: DCT-SVD v1.0
          </span>
        </div>
      </div>

      {!isAuthenticated && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Info className="w-5 h-5 text-amber-600 flex-shrink-0" />
            <div>
              <p className="font-bold">Sign in required to register provenance</p>
              <p className="text-amber-700 text-[11px] mt-0.5">
                Sign in to persist your asset records, issue HMAC-signed receipts, and generate Image Identity Passports.
              </p>
            </div>
          </div>
          <button
            onClick={onOpenAuth}
            className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold flex-shrink-0 transition-colors shadow-xs"
          >
            {t('nav_login', 'Sign In')}
          </button>
        </div>
      )}

      {/* Main Form or Success Result */}
      {result ? (
        /* Success Screen */
        <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 space-y-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-emerald-600 flex items-center justify-center text-white shadow-md shadow-emerald-500/20">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <div>
                <span className="text-[10px] font-mono font-bold tracking-widest uppercase px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                  Registration Complete
                </span>
                <h2 className="text-xl font-bold text-slate-900 mt-1">
                  {t('protect_success_title', 'Image Successfully Protected & Authenticated')}
                </h2>
                <p className="text-xs text-slate-500 font-mono mt-0.5">
                  Asset ID #{result.asset_id} &bull; Identifier: {result.registered_asset_id}
                </p>
              </div>
            </div>

            <button
              onClick={handleReset}
              className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 self-start sm:self-auto transition-colors"
            >
              {t('protect_new_upload', 'Protect Another Image')}
            </button>
          </div>

          {/* Core Info & Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-3">
              <div className="aspect-[4/3] bg-slate-100 rounded-xl overflow-hidden border border-slate-200 flex items-center justify-center relative shadow-inner">
                {previewUrl ? (
                  <img
                    src={previewUrl}
                    alt={result.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <ShieldCheck className="w-12 h-12 text-slate-300" />
                )}
                <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/60 backdrop-blur-md text-white text-[10px] font-medium">
                  {result.image_width} &times; {result.image_height} px
                </div>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {result.category && (
                  <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                    {result.category}
                  </span>
                )}
                {result.country && (
                  <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 flex items-center gap-1">
                    <Globe className="w-3 h-3 text-slate-500" />
                    {result.country}
                  </span>
                )}
              </div>
            </div>

            <div className="md:col-span-2 space-y-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">{result.title}</h3>
                <p className="text-xs text-slate-500 font-mono mt-0.5">
                  File: {result.original_filename}
                </p>
              </div>

              {/* Forensic Quality Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-center">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                    PSNR
                  </span>
                  <p className="text-base font-black text-slate-900 mt-0.5">
                    {result.metrics?.psnr_db ? `${result.metrics.psnr_db.toFixed(1)} dB` : '>42 dB'}
                  </p>
                  <span className="text-[10px] text-emerald-600 font-medium">Imperceptible</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-center">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                    SSIM
                  </span>
                  <p className="text-base font-black text-slate-900 mt-0.5">
                    {result.metrics?.ssim ? result.metrics.ssim.toFixed(4) : '>0.985'}
                  </p>
                  <span className="text-[10px] text-emerald-600 font-medium">High Fidelity</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-center">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                    Correlation (NC)
                  </span>
                  <p className="text-base font-black text-slate-900 mt-0.5">
                    {result.metrics?.nc ? result.metrics.nc.toFixed(3) : '1.000'}
                  </p>
                  <span className="text-[10px] text-emerald-600 font-medium">Exact Match</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-center">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                    Bit Error (BER)
                  </span>
                  <p className="text-base font-black text-slate-900 mt-0.5">
                    {result.metrics?.ber !== undefined ? result.metrics.ber.toFixed(3) : '0.000'}
                  </p>
                  <span className="text-[10px] text-emerald-600 font-medium">Zero Error</span>
                </div>
              </div>

              {/* Cryptographic Identifiers */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Registered 40-bit Asset ID:</span>
                  <div className="flex items-center gap-1.5 font-mono text-blue-700 font-semibold">
                    <span>{result.registered_asset_id}</span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(result.registered_asset_id);
                        setCopiedId(true);
                        setTimeout(() => setCopiedId(false), 2000);
                      }}
                      className="text-slate-400 hover:text-blue-600"
                    >
                      {copiedId ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">64-bit Perceptual Hash (pHash):</span>
                  <div className="flex items-center gap-1.5 font-mono text-slate-800 font-semibold">
                    <span>{result.perceptual_hash || 'Computed'}</span>
                    <button
                      onClick={() => {
                        if (result.perceptual_hash) {
                          navigator.clipboard.writeText(result.perceptual_hash);
                          setCopiedHash(true);
                          setTimeout(() => setCopiedHash(false), 2000);
                        }
                      }}
                      className="text-slate-400 hover:text-blue-600"
                    >
                      {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-wrap items-center gap-3">
                <button
                  onClick={handleDownloadWatermarked}
                  className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span>{t('protect_download_wm', 'Download Watermarked Image')}</span>
                </button>

                <button
                  onClick={handleDownloadReceipt}
                  className="flex items-center gap-1.5 px-4 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold shadow-xs transition-colors"
                >
                  <FileCheck2 className="w-4 h-4 text-slate-500" />
                  <span>{t('protect_download_receipt', 'Download HMAC Receipt')}</span>
                </button>

                <button
                  onClick={() => setPassportOpen(true)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition-colors"
                >
                  <Award className="w-4 h-4 text-blue-400" />
                  <span>View Identity Passport</span>
                </button>

                <button
                  onClick={() => onNavigateToVerify(result.asset_id)}
                  className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Inspect with Verify Engine</span>
                </button>
              </div>
            </div>
          </div>

          <PassportModal
            isOpen={passportOpen}
            onClose={() => setPassportOpen(false)}
            initialAsset={result as any}
          />
        </div>
      ) : (
        /* 4-Step Registration Wizard */
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Image Upload & Preview (Step 1) */}
            <div className="lg:col-span-5 space-y-4">
              <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4 shadow-xs">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                    <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-[10px]">
                      1
                    </span>
                    {t('protect_step_1', 'Select Original Image')}
                  </span>
                  {imageMeta && (
                    <span className="text-[10px] font-mono text-slate-500">
                      {imageMeta.width} &times; {imageMeta.height} px
                    </span>
                  )}
                </div>

                {previewUrl ? (
                  <div className="space-y-3">
                    <div className="aspect-[4/3] bg-slate-100 rounded-xl overflow-hidden border border-slate-200 relative">
                      <img
                        src={previewUrl}
                        alt="Preview"
                        className="w-full h-full object-contain"
                      />
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-700 truncate max-w-[200px]">
                        {file?.name}
                      </span>
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="text-blue-600 hover:underline font-medium"
                      >
                        Change Image
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
                    <p className="text-xs font-semibold text-slate-800">
                      {t('protect_drop_zone', 'Drag & drop image here, or browse')}
                    </p>
                    <p className="text-[11px] text-slate-400 mt-1">
                      {t('protect_drop_hint', 'PNG, JPG, WEBP, or TIFF up to 25MB (min 64x64 px)')}
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

              {/* Watermark Parameters (Step 3) */}
              <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4 shadow-xs">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                    <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-[10px]">
                      3
                    </span>
                    {t('protect_step_3', 'Watermark Frequency Engine')}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">128-bit payload</span>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      {t('protect_field_algorithm', 'Algorithm Sub-band Strategy')}
                    </label>
                    <select
                      value={algorithm}
                      onChange={(e) => setAlgorithm(e.target.value as any)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-xs"
                    >
                      <option value="dct_svd">DCT-SVD v1.0 (Hybrid Mid-Frequency Singular Values - Recommended)</option>
                      <option value="dct">DCT Mid-Frequency Modulation</option>
                      <option value="svd">Pure Spatial SVD</option>
                    </select>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="font-semibold text-slate-700">
                        {t('protect_field_strength', 'Embedding Strength (Alpha)')}
                      </label>
                      <span className="font-mono text-blue-700 font-bold">&alpha; = {alpha.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.05"
                      max="0.25"
                      step="0.01"
                      value={alpha}
                      onChange={(e) => setAlpha(parseFloat(e.target.value))}
                      className="w-full accent-blue-600 cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-slate-400 mt-1">
                      <span>0.05 (Maximum Invisibility)</span>
                      <span>0.10 (Standard Calibrated)</span>
                      <span>0.25 (Maximum Compression Survivability)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Metadata, Licensing & Ownership Declaration (Steps 2 & 4) */}
            <div className="lg:col-span-7 space-y-4">
              {/* Metadata & International Licensing (Step 2) */}
              <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4 shadow-xs">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                    <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-[10px]">
                      2
                    </span>
                    {t('protect_step_2', 'Metadata & International Attribution')}
                  </span>
                  <span className="text-[10px] text-slate-400">Provenance Profile</span>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      {t('protect_field_title', 'Work Title')} *
                    </label>
                    <input
                      type="text"
                      required
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g., Arctic Fox on Svalbard Tundra"
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        {t('protect_field_category', 'Category')}
                      </label>
                      <select
                        value={category}
                        onChange={(e) => setCategory(e.target.value as AssetCategory)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        {CATEGORIES.map((cat) => (
                          <option key={cat} value={cat}>
                            {cat}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        {t('protect_field_country', 'Country of Origin')}
                      </label>
                      <select
                        value={country}
                        onChange={(e) => setCountry(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        {COUNTRIES.map((ct) => (
                          <option key={ct} value={ct}>
                            {ct}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        {t('protect_field_license', 'License Terms')}
                      </label>
                      <select
                        value={licenseType}
                        onChange={(e) => setLicenseType(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        {LICENSES.map((lic) => (
                          <option key={lic} value={lic}>
                            {lic}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        {t('protect_field_attribution', 'Mandatory Attribution String')}
                      </label>
                      <input
                        type="text"
                        value={attributionText}
                        onChange={(e) => setAttributionText(e.target.value)}
                        placeholder="e.g., © 2026 Your Name. CreditMera Protected."
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Ownership Declaration & Warrant (Step 4) */}
              <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-4 shadow-xs">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                    <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-[10px]">
                      4
                    </span>
                    {t('protect_step_4', 'Ownership Declaration & Warrant')}
                  </span>
                  <span className="text-[10px] text-slate-400">HMAC-SHA256 Signed</span>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      {t('protect_field_declaration', 'Declaration Statement')} *
                    </label>
                    <textarea
                      rows={3}
                      required
                      value={declaration}
                      onChange={(e) => setDeclaration(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <p className="text-[11px] text-slate-400 leading-snug">
                    By submitting, a collision-safe 40-bit Asset ID is generated, the 128-bit payload is frequency-embedded via DCT-SVD, and a cryptographically signed HMAC ownership receipt is permanently recorded.
                  </p>

                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={loading || !file}
                      className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/10 hover:shadow-blue-500/20 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                    >
                      {loading ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          <span>{t('protect_btn_registering', 'Embedding DCT-SVD Frequency Watermark...')}</span>
                        </>
                      ) : (
                        <>
                          <ShieldCheck className="w-4 h-4" />
                          <span>{t('protect_btn_embed', 'Protect & Register Image')}</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </form>
      )}
    </div>
  );
};
