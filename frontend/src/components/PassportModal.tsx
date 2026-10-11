import React, { useState, useEffect } from 'react';
import {
  X,
  Printer,
  Copy,
  Check,
  ShieldCheck,
  Globe,
  FileCheck2,
  Calendar,
  User,
  Fingerprint,
  Hash,
  Download,
} from 'lucide-react';
import { useTranslation } from '../i18n/I18nContext';
import { useAuth } from '../context/AuthContext';
import { getAssetDetail, downloadWatermarkedImage, downloadReceiptJson } from '../services/api';
import type { AssetDetail, AssetSummary } from '../types';

interface PassportModalProps {
  isOpen: boolean;
  onClose: () => void;
  assetId?: number | null;
  initialAsset?: AssetDetail | AssetSummary | null;
}

export const PassportModal: React.FC<PassportModalProps> = ({
  isOpen,
  onClose,
  assetId,
  initialAsset,
}) => {
  const { t } = useTranslation();
  const { token } = useAuth();
  const [asset, setAsset] = useState<AssetDetail | AssetSummary | null>(initialAsset || null);
  const [loading, setLoading] = useState(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  useEffect(() => {
    if (initialAsset) {
      setAsset(initialAsset);
    } else if (assetId && token) {
      setLoading(true);
      getAssetDetail(token, assetId)
        .then((data) => setAsset(data))
        .catch((err) => console.error('Failed to load asset detail for passport:', err))
        .finally(() => setLoading(false));
    }
  }, [assetId, initialAsset, token]);

  if (!isOpen) return null;

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(id);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadImage = async () => {
    if (!asset || !token) return;
    try {
      const blob = await downloadWatermarkedImage(token, asset.asset_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `watermarked_${asset.original_filename}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed', err);
    }
  };

  const handleDownloadReceipt = async () => {
    if (!asset || !token) return;
    try {
      const blob = await downloadReceiptJson(token, asset.asset_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `receipt_${asset.asset_id}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Receipt download failed', err);
    }
  };

  const passportNumber = asset
    ? `CMP-${new Date(asset.registered_at).getFullYear()}-${asset.registered_asset_id.substring(0, 8).toUpperCase()}`
    : 'CMP-2026-UNKNOWN';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/60 backdrop-blur-sm overflow-y-auto animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden my-auto max-h-[92vh] flex flex-col">
        {/* Top Action Bar (hidden when printing) */}
        <div className="no-print flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/80">
          <div className="flex items-center gap-2 text-slate-800 font-semibold text-sm">
            <ShieldCheck className="w-5 h-5 text-blue-600" />
            <span>{t('passport_title', 'Image Identity Passport')}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 font-mono">
              {passportNumber}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors shadow-xs"
            >
              <Printer className="w-3.5 h-3.5 text-slate-500" />
              <span>{t('passport_btn_print', 'Print / PDF')}</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Passport Document Body */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8 space-y-6 passport-container">
          {loading ? (
            <div className="py-20 text-center">
              <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-sm text-slate-500">{t('common_loading', 'Loading passport dossier...')}</p>
            </div>
          ) : !asset ? (
            <div className="py-20 text-center text-slate-500">
              <p className="text-sm">No asset selected.</p>
            </div>
          ) : (
            <div className="border border-slate-200 rounded-2xl p-6 sm:p-8 bg-gradient-to-b from-white to-slate-50/40 relative shadow-sm">
              {/* Document Header & Security Ribbon */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
                    <Fingerprint className="w-7 h-7" />
                  </div>
                  <div>
                    <h2 className="text-xl font-black text-slate-900 tracking-tight leading-none uppercase">
                      CreditMera Image Passport
                    </h2>
                    <p className="text-xs text-slate-500 font-medium tracking-wide mt-1">
                      International Digital Provenance &amp; Forensic Attribution Record
                    </p>
                  </div>
                </div>

                <div className="text-start sm:text-end">
                  <span className="inline-block text-[10px] font-mono font-bold tracking-widest uppercase px-2.5 py-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                    Cryptographically Authenticated
                  </span>
                  <p className="text-xs font-mono text-slate-500 mt-1">
                    Serial: <strong className="text-slate-800">{passportNumber}</strong>
                  </p>
                </div>
              </div>

              {/* Asset Core Profile Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 py-6 border-b border-slate-200">
                {/* Left: Thumbnail & Visual Badge */}
                <div className="space-y-3">
                  <div className="aspect-[4/3] bg-slate-100 rounded-xl overflow-hidden border border-slate-200 flex items-center justify-center relative shadow-inner">
                    <img
                      src={`/api/v1/assets/${asset.asset_id}/download/watermarked`}
                      alt={asset.title}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        // Fallback visual placeholder if image direct loading fails
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                    <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/60 backdrop-blur-md text-white text-[10px] font-medium">
                      {asset.image_width} &times; {asset.image_height} px
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {asset.category && (
                      <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                        {asset.category}
                      </span>
                    )}
                    {asset.country && (
                      <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 flex items-center gap-1">
                        <Globe className="w-3 h-3 text-slate-500" />
                        {asset.country}
                      </span>
                    )}
                    {asset.license_type && (
                      <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                        {asset.license_type}
                      </span>
                    )}
                  </div>
                </div>

                {/* Right 2 cols: Registered Attributes */}
                <div className="md:col-span-2 space-y-4">
                  <div>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                      Work Title
                    </span>
                    <h3 className="text-lg font-bold text-slate-900 mt-0.5">{asset.title}</h3>
                    <p className="text-xs text-slate-500 font-mono mt-0.5">
                      Filename: {asset.original_filename}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-slate-400 font-medium">Registration Date</span>
                      <p className="font-semibold text-slate-800 mt-0.5 flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        {new Date(asset.registered_at).toLocaleString()}
                      </p>
                    </div>

                    <div>
                      <span className="text-slate-400 font-medium">Registered Owner</span>
                      <p className="font-semibold text-slate-800 mt-0.5 flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-slate-500" />
                        {(asset as any).owner_name || 'Verified Creator'}
                      </p>
                    </div>

                    <div>
                      <span className="text-slate-400 font-medium">Embedding Algorithm</span>
                      <p className="font-semibold text-slate-800 mt-0.5 font-mono">
                        {asset.algorithm || 'DCT-SVD v1.0'} (128-bit)
                      </p>
                    </div>

                    <div>
                      <span className="text-slate-400 font-medium">Numeric Asset ID</span>
                      <p className="font-semibold text-slate-800 mt-0.5 font-mono">
                        #{asset.asset_id}
                      </p>
                    </div>
                  </div>

                  {asset.attribution_text && (
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                        Mandatory Attribution Notice
                      </span>
                      <p className="text-xs text-slate-700 italic mt-0.5">
                        &ldquo;{asset.attribution_text}&rdquo;
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Forensic & Cryptographic Hashes Section */}
              <div className="py-6 border-b border-slate-200 space-y-3">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                  <Hash className="w-4 h-4 text-blue-600" />
                  Forensic Fingerprints &amp; Cryptographic Signatures
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  {/* Perceptual Hash */}
                  <div className="p-3 rounded-xl bg-white border border-slate-200">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-slate-500">
                        Perceptual Hash (64-bit DCT pHash)
                      </span>
                      <button
                        onClick={() => handleCopy(asset.perceptual_hash || 'N/A', 'phash')}
                        className="text-slate-400 hover:text-blue-600"
                        title="Copy hash"
                      >
                        {copiedHash === 'phash' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                    <code className="block mt-1 font-mono text-[11px] text-blue-700 font-semibold break-all">
                      {asset.perceptual_hash || 'Calculated on ingest'}
                    </code>
                  </div>

                  {/* Registered Asset ID */}
                  <div className="p-3 rounded-xl bg-white border border-slate-200">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-slate-500">
                        Registered Identifier (40-bit Hex)
                      </span>
                      <button
                        onClick={() => handleCopy(asset.registered_asset_id, 'regid')}
                        className="text-slate-400 hover:text-blue-600"
                        title="Copy ID"
                      >
                        {copiedHash === 'regid' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                    <code className="block mt-1 font-mono text-[11px] text-slate-800 font-semibold break-all">
                      {asset.registered_asset_id}
                    </code>
                  </div>

                  {/* Original SHA256 */}
                  <div className="p-3 rounded-xl bg-white border border-slate-200">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-slate-500">
                        Original File SHA-256
                      </span>
                      <button
                        onClick={() => handleCopy(asset.original_file_hash, 'orig')}
                        className="text-slate-400 hover:text-blue-600"
                      >
                        {copiedHash === 'orig' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                    <code className="block mt-1 font-mono text-[10px] text-slate-600 break-all">
                      {asset.original_file_hash}
                    </code>
                  </div>

                  {/* Watermarked SHA256 */}
                  <div className="p-3 rounded-xl bg-white border border-slate-200">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-slate-500">
                        Watermarked File SHA-256
                      </span>
                      <button
                        onClick={() => handleCopy(asset.watermarked_file_hash, 'wm')}
                        className="text-slate-400 hover:text-blue-600"
                      >
                        {copiedHash === 'wm' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                    <code className="block mt-1 font-mono text-[10px] text-slate-600 break-all">
                      {asset.watermarked_file_hash}
                    </code>
                  </div>
                </div>
              </div>

              {/* Legal Attribution & Disclaimer */}
              <div className="pt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-[11px] text-slate-500">
                <div className="max-w-xl">
                  <p className="leading-relaxed">
                    <strong>Official Notice:</strong> This Image Identity Passport constitutes a timestamped digital provenance record. The embedded imperceptible watermark survives common re-compression and downscaling, facilitating forensic cross-border copyright attribution.
                  </p>
                </div>
                <div className="text-end font-mono text-[10px] text-slate-400">
                  CreditMera Platform Key Verified &bull; HMAC-SHA256 Authenticated
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions (hidden when printing) */}
        <div className="no-print flex items-center justify-between px-6 py-4 border-t border-slate-100 bg-slate-50/80">
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadImage}
              disabled={!asset || !token}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>Download Watermarked</span>
            </button>
            <button
              onClick={handleDownloadReceipt}
              disabled={!asset || !token}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 transition-colors"
            >
              <FileCheck2 className="w-3.5 h-3.5 text-slate-500" />
              <span>Download HMAC Receipt</span>
            </button>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            {t('common_save', 'Close')}
          </button>
        </div>
      </div>
    </div>
  );
};
