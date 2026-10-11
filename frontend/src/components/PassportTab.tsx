import React, { useState, useEffect } from 'react';
import {
  Award,
  Search,
  Printer,
  Copy,
  Check,
  Globe,
  Fingerprint,
  Calendar,
  User,
  Download,
  FileCheck2,
  ExternalLink,
  Hash,
} from 'lucide-react';
import { useTranslation } from '../i18n/I18nContext';
import { useAuth } from '../context/AuthContext';
import { listAssets, getAssetDetail, downloadWatermarkedImage, downloadReceiptJson } from '../services/api';
import type { AssetSummary, AssetDetail } from '../types';

interface PassportTabProps {
  onNavigateToProtect?: () => void;
  onNavigateToVerify?: (assetId: number) => void;
  initialAssetId?: number;
}

export const PassportTab: React.FC<PassportTabProps> = ({
  onNavigateToProtect,
  onNavigateToVerify,
  initialAssetId,
}) => {
  const { t } = useTranslation();
  const { token, isAuthenticated } = useAuth();

  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(initialAssetId || null);
  const [assetDetail, setAssetDetail] = useState<AssetDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedField, setCopiedField] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      listAssets(token, 0, 50)
        .then((data) => {
          setAssets(data);
          if (!selectedAssetId && data.length > 0) {
            setSelectedAssetId(data[0].asset_id);
          }
        })
        .catch((err) => console.error('Failed to list assets for passport tab:', err));
    }
  }, [token]);

  useEffect(() => {
    if (selectedAssetId && token) {
      setLoading(true);
      getAssetDetail(token, selectedAssetId)
        .then((detail) => setAssetDetail(detail))
        .catch((err) => console.error('Failed to load asset detail:', err))
        .finally(() => setLoading(false));
    }
  }, [selectedAssetId, token]);

  const handleCopy = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadImage = async () => {
    if (!assetDetail || !token) return;
    try {
      const blob = await downloadWatermarkedImage(token, assetDetail.asset_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `watermarked_${assetDetail.original_filename}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed', err);
    }
  };

  const handleDownloadReceipt = async () => {
    if (!assetDetail || !token) return;
    try {
      const blob = await downloadReceiptJson(token, assetDetail.asset_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `receipt_${assetDetail.asset_id}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download receipt failed', err);
    }
  };

  const filteredAssets = assets.filter((a) =>
    a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.registered_asset_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (a.category && a.category.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (a.country && a.country.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const passportNumber = assetDetail
    ? `CMP-${new Date(assetDetail.registered_at).getFullYear()}-${assetDetail.registered_asset_id.substring(0, 8).toUpperCase()}`
    : 'CMP-2026-PENDING';

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="no-print flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-100 rounded-lg text-blue-600">
              <Award className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold text-slate-900">
              {t('passport_title', 'Image Identity Passport')}
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            {t('passport_subtitle', 'Digital provenance profile, forensic hashes, and international copyright attribution for registered assets.')}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {assetDetail && (
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-xs transition-colors"
            >
              <Printer className="w-3.5 h-3.5 text-slate-500" />
              <span>{t('passport_btn_print', 'Print / Save PDF')}</span>
            </button>
          )}
          {onNavigateToProtect && (
            <button
              onClick={onNavigateToProtect}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition-colors"
            >
              <span>{t('nav_protect', 'Protect New Image')}</span>
            </button>
          )}
        </div>
      </div>

      {!isAuthenticated ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-xs">
          <Award className="w-12 h-12 text-blue-500 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-900">Sign in to view Image Passports</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
            Access certified provenance credentials for your protected catalog.
          </p>
        </div>
      ) : assets.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-xs">
          <Award className="w-12 h-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-900">No registered assets found</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
            Protect and register your first image to generate its certified Digital Provenance Passport.
          </p>
          {onNavigateToProtect && (
            <button
              onClick={onNavigateToProtect}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors"
            >
              {t('nav_protect', 'Protect Image Now')}
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Column: Asset Selector (Hidden on print) */}
          <div className="no-print lg:col-span-1 space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search registered images..."
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100 max-h-[600px] overflow-y-auto shadow-xs">
              {filteredAssets.map((asset) => {
                const isSelected = selectedAssetId === asset.asset_id;
                return (
                  <button
                    key={asset.asset_id}
                    onClick={() => setSelectedAssetId(asset.asset_id)}
                    className={`w-full text-start p-3 transition-colors flex items-center gap-3 ${
                      isSelected
                        ? 'bg-blue-50 border-s-4 border-s-blue-600'
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className="w-10 h-10 rounded-lg bg-slate-100 overflow-hidden flex-shrink-0 border border-slate-200">
                      <img
                        src={`/api/v1/assets/${asset.asset_id}/download/watermarked`}
                        alt={asset.title}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = 'none';
                        }}
                      />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-slate-900 truncate">{asset.title}</p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[10px] text-slate-400 font-mono">#{asset.asset_id}</span>
                        {asset.country && (
                          <span className="text-[10px] text-slate-500 flex items-center gap-0.5">
                            &bull; {asset.country}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Column: Passport Document */}
          <div className="lg:col-span-3">
            {loading ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-20 text-center shadow-xs">
                <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mb-3" />
                <p className="text-xs text-slate-500">Loading digital passport records...</p>
              </div>
            ) : !assetDetail ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 shadow-xs">
                Select an asset from the list to preview its identity passport.
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 space-y-6 shadow-sm passport-container">
                {/* Header Badge */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 flex-shrink-0">
                      <Fingerprint className="w-7 h-7" />
                    </div>
                    <div>
                      <h2 className="text-xl font-black text-slate-900 tracking-tight leading-none uppercase">
                        CreditMera Image Identity Passport
                      </h2>
                      <p className="text-xs text-slate-500 font-medium tracking-wide mt-1">
                        International Digital Provenance &amp; Attribution Certificate
                      </p>
                    </div>
                  </div>

                  <div className="text-start sm:text-end">
                    <span className="inline-block text-[10px] font-mono font-bold tracking-widest uppercase px-2.5 py-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                      Authenticity Sealed
                    </span>
                    <p className="text-xs font-mono text-slate-500 mt-1">
                      Certificate: <strong className="text-slate-800">{passportNumber}</strong>
                    </p>
                  </div>
                </div>

                {/* Profile Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 py-4 border-b border-slate-200">
                  <div className="space-y-3">
                    <div className="aspect-[4/3] bg-slate-100 rounded-xl overflow-hidden border border-slate-200 flex items-center justify-center relative shadow-inner">
                      <img
                        src={`/api/v1/assets/${assetDetail.asset_id}/download/watermarked`}
                        alt={assetDetail.title}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = 'none';
                        }}
                      />
                      <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/60 backdrop-blur-md text-white text-[10px] font-medium">
                        {assetDetail.image_width} &times; {assetDetail.image_height} px
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-1.5">
                      {assetDetail.category && (
                        <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                          {assetDetail.category}
                        </span>
                      )}
                      {assetDetail.country && (
                        <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 flex items-center gap-1">
                          <Globe className="w-3 h-3 text-slate-500" />
                          {assetDetail.country}
                        </span>
                      )}
                      {assetDetail.license_type && (
                        <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                          {assetDetail.license_type}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="md:col-span-2 space-y-4">
                    <div>
                      <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                        Work Title
                      </span>
                      <h3 className="text-lg font-bold text-slate-900 mt-0.5">{assetDetail.title}</h3>
                      <p className="text-xs text-slate-500 font-mono mt-0.5">
                        Filename: {assetDetail.original_filename}
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-xs">
                      <div>
                        <span className="text-slate-400 font-medium">Registration Date</span>
                        <p className="font-semibold text-slate-800 mt-0.5 flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-slate-500" />
                          {new Date(assetDetail.registered_at).toLocaleString()}
                        </p>
                      </div>

                      <div>
                        <span className="text-slate-400 font-medium">Registered Owner</span>
                        <p className="font-semibold text-slate-800 mt-0.5 flex items-center gap-1.5">
                          <User className="w-3.5 h-3.5 text-slate-500" />
                          {assetDetail.owner_name || 'Verified Creator'}
                        </p>
                      </div>

                      <div>
                        <span className="text-slate-400 font-medium">Algorithm Engine</span>
                        <p className="font-semibold text-slate-800 mt-0.5 font-mono">
                          {assetDetail.algorithm} ({assetDetail.algorithm_version})
                        </p>
                      </div>

                      <div>
                        <span className="text-slate-400 font-medium">Modulation Alpha</span>
                        <p className="font-semibold text-slate-800 mt-0.5 font-mono">
                          &alpha; = {assetDetail.alpha}
                        </p>
                      </div>
                    </div>

                    {assetDetail.attribution_text && (
                      <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                        <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                          Attribution Clause
                        </span>
                        <p className="text-xs text-slate-700 italic mt-0.5">
                          &ldquo;{assetDetail.attribution_text}&rdquo;
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Hashes & Fingerprints */}
                <div className="py-4 border-b border-slate-200 space-y-3">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                    <Hash className="w-4 h-4 text-blue-600" />
                    Cryptographic &amp; Perceptual Fingerprints
                  </h4>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold text-slate-600">
                          Perceptual Hash (64-bit DCT pHash)
                        </span>
                        <button
                          onClick={() => handleCopy(assetDetail.perceptual_hash || '', 'phash')}
                          className="text-slate-400 hover:text-blue-600"
                        >
                          {copiedField === 'phash' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                      <code className="block mt-1 font-mono text-[11px] text-blue-700 font-semibold break-all">
                        {assetDetail.perceptual_hash || 'Computed'}
                      </code>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold text-slate-600">
                          Registered Identifier (40-bit Hex)
                        </span>
                        <button
                          onClick={() => handleCopy(assetDetail.registered_asset_id, 'regid')}
                          className="text-slate-400 hover:text-blue-600"
                        >
                          {copiedField === 'regid' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                      <code className="block mt-1 font-mono text-[11px] text-slate-800 font-semibold break-all">
                        {assetDetail.registered_asset_id}
                      </code>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold text-slate-600">
                          Original File SHA-256
                        </span>
                        <button
                          onClick={() => handleCopy(assetDetail.original_file_hash, 'orig')}
                          className="text-slate-400 hover:text-blue-600"
                        >
                          {copiedField === 'orig' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                      <code className="block mt-1 font-mono text-[10px] text-slate-600 break-all">
                        {assetDetail.original_file_hash}
                      </code>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold text-slate-600">
                          Watermarked File SHA-256
                        </span>
                        <button
                          onClick={() => handleCopy(assetDetail.watermarked_file_hash, 'wm')}
                          className="text-slate-400 hover:text-blue-600"
                        >
                          {copiedField === 'wm' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                      <code className="block mt-1 font-mono text-[10px] text-slate-600 break-all">
                        {assetDetail.watermarked_file_hash}
                      </code>
                    </div>
                  </div>
                </div>

                {/* Bottom Actions */}
                <div className="no-print pt-2 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleDownloadImage}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors shadow-xs"
                    >
                      <Download className="w-3.5 h-3.5 text-slate-500" />
                      <span>Download Watermarked Image</span>
                    </button>
                    <button
                      onClick={handleDownloadReceipt}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors shadow-xs"
                    >
                      <FileCheck2 className="w-3.5 h-3.5 text-slate-500" />
                      <span>Download HMAC Receipt</span>
                    </button>
                  </div>

                  {onNavigateToVerify && (
                    <button
                      onClick={() => onNavigateToVerify(assetDetail.asset_id)}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>Inspect with Verify Engine</span>
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
