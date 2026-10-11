import React, { useState, useEffect } from 'react';
import {
  Database,
  Search,
  Download,
  RefreshCw,
  Layers,
  Award,
  Globe,
  Grid,
  List,
  FileCheck2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../i18n/I18nContext';
import {
  listAssets,
  downloadWatermarkedImage,
  downloadReceiptJson,
  searchVaultSimilarity,
} from '../services/api';
import type { AssetSummary, SimilaritySearchResult } from '../types';
import { PassportModal } from './PassportModal';

const CATEGORIES = [
  'All',
  'Wildlife',
  'Nature',
  'Travel',
  'Landscape',
  'Portrait',
  'Fashion',
  'Architecture',
  'Documentary',
  'Other',
];

const COUNTRIES = [
  'All',
  'United States',
  'India',
  'United Kingdom',
  'Germany',
  'France',
  'Japan',
  'Canada',
  'Australia',
  'Other',
];

interface AssetVaultTabProps {
  onOpenAuth: () => void;
  onNavigateToProtect: () => void;
  onNavigateToVerify: (assetId: number) => void;
  onNavigateToCases?: (assetId: number) => void;
  onOpenPassport?: (asset: AssetSummary) => void;
  initialSearchQuery?: string;
}

export const AssetVaultTab: React.FC<AssetVaultTabProps> = ({
  onOpenAuth,
  onNavigateToProtect,
  onNavigateToVerify,
  onNavigateToCases,
  onOpenPassport,
  initialSearchQuery = '',
}) => {
  const { t } = useTranslation();
  const { token, isAuthenticated } = useAuth();

  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & Views
  const [searchQuery, setSearchQuery] = useState(initialSearchQuery);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedCountry, setSelectedCountry] = useState('All');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Modals & Details
  const [passportAsset, setPassportAsset] = useState<AssetSummary | null>(null);

  // Perceptual Search state
  const [simSearchOpen, setSimSearchOpen] = useState(false);
  const [simSearchFile, setSimSearchFile] = useState<File | null>(null);
  const [simSearching, setSimSearching] = useState(false);
  const [simSearchResult, setSimSearchResult] = useState<SimilaritySearchResult | null>(null);

  const fetchAssets = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listAssets(
        token,
        0,
        50,
        selectedCategory === 'All' ? undefined : selectedCategory,
        selectedCountry === 'All' ? undefined : selectedCountry
      );
      setAssets(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load assets from server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchAssets();
    }
  }, [isAuthenticated, token, selectedCategory, selectedCountry]);

  useEffect(() => {
    if (initialSearchQuery) {
      setSearchQuery(initialSearchQuery);
    }
  }, [initialSearchQuery]);

  const handleDownloadImage = async (assetId: number, title: string) => {
    if (!token) return;
    try {
      const blob = await downloadWatermarkedImage(token, assetId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `creditmera_${assetId}_${title.replace(/[^a-zA-Z0-9_-]/g, '_')}.png`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(`Download failed: ${err?.message}`);
    }
  };

  const handleDownloadReceipt = async (assetId: number) => {
    if (!token) return;
    try {
      const blob = await downloadReceiptJson(token, assetId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `receipt_${assetId}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(`Receipt download failed: ${err?.message}`);
    }
  };

  const handleSimSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!simSearchFile) return;
    setSimSearching(true);
    try {
      const res = await searchVaultSimilarity(simSearchFile, undefined, token || undefined);
      setSimSearchResult(res);
    } catch (err: any) {
      alert(`Visual similarity search failed: ${err.message}`);
    } finally {
      setSimSearching(false);
    }
  };

  const filteredAssets = assets.filter((a) => {
    const q = searchQuery.toLowerCase();
    const matchesQuery =
      a.title.toLowerCase().includes(q) ||
      a.asset_id.toString().includes(q) ||
      a.registered_asset_id.toLowerCase().includes(q) ||
      a.original_filename.toLowerCase().includes(q) ||
      (a.perceptual_hash && a.perceptual_hash.toLowerCase().includes(q));
    return matchesQuery;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-100 rounded-lg text-blue-600">
              <Database className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold text-slate-900">
              {t('vault_title', 'Asset Vault & Digital Registry')}
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            {t(
              'vault_subtitle',
              'Browse registered digital works, verify cryptographic provenance, and issue Image Identity Passports.'
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setSimSearchOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-purple-700 bg-purple-50 border border-purple-200 rounded-lg hover:bg-purple-100 transition-colors"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>{t('vault_btn_sim_search', 'Search Visual Similarity')}</span>
          </button>

          <button
            onClick={onNavigateToProtect}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition-colors"
          >
            <span>{t('nav_protect', 'Protect New Image')}</span>
          </button>
        </div>
      </div>

      {!isAuthenticated ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-xs">
          <Database className="w-12 h-12 text-blue-500 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-900">{t('vault_signin_title', 'Sign in to view your Asset Vault')}</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
            {t('vault_signin_desc', 'Manage your registered images, export signed receipts, and monitor cross-border attribution.')}
          </p>
          <button
            onClick={onOpenAuth}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors"
          >
            {t('nav_login', 'Sign In Now')}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Controls Bar: Search, Category Pills, Country Selector, View Toggle */}
          <div className="bg-white p-3.5 rounded-xl border border-slate-200 space-y-3 shadow-xs">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t('vault_search_placeholder', 'Search by title, asset ID, hash or filename...')}
                  className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center gap-2">
                {/* Country Filter */}
                <select
                  value={selectedCountry}
                  onChange={(e) => setSelectedCountry(e.target.value)}
                  className="py-1 px-2.5 text-xs bg-white border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {COUNTRIES.map((c) => (
                    <option key={c} value={c}>
                      {c === 'All' ? t('common_all', 'All Countries') : c}
                    </option>
                  ))}
                </select>

                {/* View Mode Toggle */}
                <div className="flex items-center border border-slate-200 rounded-lg p-0.5 bg-slate-50">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-1.5 rounded ${viewMode === 'grid' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-400 hover:text-slate-600'}`}
                    title="Grid view"
                  >
                    <Grid className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`p-1.5 rounded ${viewMode === 'list' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-400 hover:text-slate-600'}`}
                    title="List view"
                  >
                    <List className="w-3.5 h-3.5" />
                  </button>
                </div>

                <button
                  onClick={fetchAssets}
                  className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
                  title="Refresh vault"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>

            {/* Category Filter Pills */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-1 text-xs">
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mr-1">
                Category:
              </span>
              {CATEGORIES.map((cat) => {
                const isSelected = selectedCategory === cat;
                return (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                      isSelected
                        ? 'bg-blue-600 text-white font-semibold'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200/70'
                    }`}
                  >
                    {cat}
                  </button>
                );
              })}
            </div>
          </div>

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl">
              {error}
            </div>
          )}

          {/* Asset List or Grid */}
          {loading ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-16 text-center">
              <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-xs text-slate-500">Loading catalog...</p>
            </div>
          ) : filteredAssets.length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-xs">
              <Database className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-slate-800">No assets found</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
                {searchQuery || selectedCategory !== 'All' || selectedCountry !== 'All'
                  ? 'No images match the current filter criteria.'
                  : 'Your vault is currently empty. Protect and register your first image.'}
              </p>
              <button
                onClick={onNavigateToProtect}
                className="px-3.5 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors"
              >
                Protect Image Now
              </button>
            </div>
          ) : viewMode === 'grid' ? (
            /* Grid View */
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {filteredAssets.map((asset) => (
                <div
                  key={asset.asset_id}
                  className="bg-white rounded-xl border border-slate-200 shadow-xs hover:shadow-card hover:border-slate-300 transition-all flex flex-col justify-between overflow-hidden group"
                >
                  <div className="p-4 space-y-3">
                    <div className="aspect-[16/10] bg-slate-100 rounded-lg overflow-hidden border border-slate-200 relative">
                      <img
                        src={`/api/v1/assets/${asset.asset_id}/download/watermarked`}
                        alt={asset.title}
                        className="w-full h-full object-cover group-hover:scale-102 transition-transform duration-300"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = 'none';
                        }}
                      />
                      <div className="absolute top-2 left-2 flex items-center gap-1">
                        {asset.category && (
                          <span className="px-2 py-0.5 rounded bg-black/60 backdrop-blur-md text-white text-[10px] font-medium">
                            {asset.category}
                          </span>
                        )}
                        {asset.country && (
                          <span className="px-2 py-0.5 rounded bg-white/90 backdrop-blur-md text-slate-800 text-[10px] font-semibold border border-slate-200 flex items-center gap-1">
                            <Globe className="w-3 h-3 text-slate-500" />
                            {asset.country}
                          </span>
                        )}
                      </div>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-slate-900 truncate">{asset.title}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] text-slate-400 font-mono">
                          #{asset.asset_id}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono truncate max-w-[140px]">
                          pHash: {asset.perceptual_hash?.substring(0, 10)}...
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="px-4 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between gap-1 text-xs">
                    <button
                      onClick={() => {
                        if (onOpenPassport) {
                          onOpenPassport(asset);
                        } else {
                          setPassportAsset(asset);
                        }
                      }}
                      className="flex items-center gap-1 font-semibold text-blue-600 hover:text-blue-700 transition-colors"
                    >
                      <Award className="w-3.5 h-3.5" />
                      <span>Passport</span>
                    </button>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => onNavigateToVerify(asset.asset_id)}
                        className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-white rounded transition-colors"
                        title="Inspect with Verify Engine"
                      >
                        <Search className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={() => handleDownloadImage(asset.asset_id, asset.title)}
                        className="p-1.5 text-slate-400 hover:text-slate-800 hover:bg-white rounded transition-colors"
                        title="Download watermarked image"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={() => handleDownloadReceipt(asset.asset_id)}
                        className="p-1.5 text-slate-400 hover:text-slate-800 hover:bg-white rounded transition-colors"
                        title="Download HMAC receipt"
                      >
                        <FileCheck2 className="w-3.5 h-3.5" />
                      </button>

                      {onNavigateToCases && (
                        <button
                          onClick={() => onNavigateToCases(asset.asset_id)}
                          className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-white rounded transition-colors"
                          title="Open Global Case"
                        >
                          <Globe className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* List View */
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
              <table className="w-full text-start text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4 text-start">ID</th>
                    <th className="py-3 px-4 text-start">Title</th>
                    <th className="py-3 px-4 text-start">Category</th>
                    <th className="py-3 px-4 text-start">Country</th>
                    <th className="py-3 px-4 text-start">pHash</th>
                    <th className="py-3 px-4 text-start">Registered</th>
                    <th className="py-3 px-4 text-end">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {filteredAssets.map((asset) => (
                    <tr key={asset.asset_id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-blue-700">
                        #{asset.asset_id}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-900">
                        {asset.title}
                      </td>
                      <td className="py-3 px-4">
                        {asset.category ? (
                          <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-semibold">
                            {asset.category}
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {asset.country || '—'}
                      </td>
                      <td className="py-3 px-4 font-mono text-[10px] text-slate-500">
                        {asset.perceptual_hash?.substring(0, 12)}...
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {new Date(asset.registered_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-end">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => {
                              if (onOpenPassport) onOpenPassport(asset);
                              else setPassportAsset(asset);
                            }}
                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                            title="View passport"
                          >
                            <Award className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => onNavigateToVerify(asset.asset_id)}
                            className="p-1.5 text-slate-500 hover:bg-slate-100 rounded"
                            title="Inspect"
                          >
                            <Search className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDownloadImage(asset.asset_id, asset.title)}
                            className="p-1.5 text-slate-500 hover:bg-slate-100 rounded"
                            title="Download"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>
                          {onNavigateToCases && (
                            <button
                              onClick={() => onNavigateToCases(asset.asset_id)}
                              className="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-slate-100 rounded"
                              title="Open Global Case"
                            >
                              <Globe className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Passport Modal */}
      {passportAsset && (
        <PassportModal
          isOpen={Boolean(passportAsset)}
          onClose={() => setPassportAsset(null)}
          initialAsset={passportAsset}
        />
      )}

      {/* Visual Similarity Search Modal */}
      {simSearchOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-purple-600" />
                <h3 className="text-base font-bold text-slate-900">
                  Search Vault for Visual Resemblance
                </h3>
              </div>
              <button
                onClick={() => {
                  setSimSearchOpen(false);
                  setSimSearchResult(null);
                  setSimSearchFile(null);
                }}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleSimSearchSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Upload Query Image to Find Visually Similar Matches in Vault
                </label>
                <input
                  type="file"
                  accept="image/*"
                  required
                  onChange={(e) => setSimSearchFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
                />
              </div>

              <button
                type="submit"
                disabled={simSearching || !simSearchFile}
                className="w-full py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold transition-colors disabled:opacity-50"
              >
                {simSearching ? 'Computing Perceptual Hashes...' : 'Scan Vault with 64-bit pHash'}
              </button>
            </form>

            {simSearchResult && (
              <div className="space-y-3 pt-3 border-t border-slate-100 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">
                    Matches Found: {simSearchResult.matches.length}
                  </span>
                  <span className="text-[11px] font-mono text-slate-400">
                    pHash: {simSearchResult.query_phash}
                  </span>
                </div>

                {simSearchResult.matches.length === 0 ? (
                  <p className="text-slate-500 py-3 text-center">
                    No visually similar registered images found (Hamming distance &gt; 15).
                  </p>
                ) : (
                  <div className="divide-y divide-slate-100 max-h-56 overflow-y-auto">
                    {simSearchResult.matches.map((match) => (
                      <div key={match.asset_id} className="py-2.5 flex items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold text-slate-900">{match.title}</p>
                          <p className="text-[11px] text-slate-400">
                            Asset #{match.asset_id} &bull; Distance: {match.hamming_distance}/64
                          </p>
                        </div>
                        <div className="text-end">
                          <span className="font-bold text-purple-700 block">
                            {match.similarity_percentage.toFixed(1)}% match
                          </span>
                          <span className="text-[10px] text-slate-500">
                            {match.similarity_tier}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
