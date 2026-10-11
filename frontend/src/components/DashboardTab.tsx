import React, { useState, useEffect } from 'react';
import {
  UploadCloud,
  Search,
  Database,
  Award,
  Globe,
  ShieldCheck,
  TrendingUp,
  FileCheck2,
  ArrowRight,
  ExternalLink,
  Lock,
} from 'lucide-react';
import { useTranslation } from '../i18n/I18nContext';
import { useAuth } from '../context/AuthContext';
import { listAssets, listCases } from '../services/api';
import type { AssetSummary, GlobalCase } from '../types';

interface DashboardTabProps {
  onNavigateToProtect: () => void;
  onNavigateToVerify: (assetId?: number) => void;
  onNavigateToVault: () => void;
  onNavigateToCases: () => void;
  onNavigateToLab: () => void;
  onOpenPassport: (asset: AssetSummary) => void;
}

export const DashboardTab: React.FC<DashboardTabProps> = ({
  onNavigateToProtect,
  onNavigateToVerify,
  onNavigateToVault,
  onNavigateToCases,
  onNavigateToLab,
  onOpenPassport,
}) => {
  const { t } = useTranslation();
  const { user, token, isAuthenticated } = useAuth();

  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [cases, setCases] = useState<GlobalCase[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (token) {
      setLoading(true);
      Promise.all([
        listAssets(token, 0, 8).catch(() => []),
        listCases(token, undefined, undefined, 0, 5).catch(() => []),
      ])
        .then(([assetsData, casesData]) => {
          setAssets(assetsData);
          setCases(casesData);
        })
        .finally(() => setLoading(false));
    }
  }, [token]);

  return (
    <div className="space-y-8">
      {/* Welcome Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-700 p-8 text-white shadow-lg">
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 backdrop-blur-md text-xs font-semibold text-blue-50 border border-white/20">
            <ShieldCheck className="w-4 h-4 text-emerald-300" />
            <span>International Creative-Tech SaaS Platform</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-black tracking-tight leading-tight">
            {isAuthenticated && user?.full_name
              ? `${t('dash_welcome_title', 'Welcome back,')} ${user.full_name}`
              : t('dash_welcome_title', 'Welcome to CreditMera')}
          </h1>

          <p className="text-sm text-blue-100 leading-relaxed max-w-2xl font-normal">
            {t(
              'dash_welcome_subtitle',
              'Protect, verify, and enforce copyright attribution worldwide. Powered by imperceptible DCT-SVD frequency watermarking and 64-bit perceptual hashing.'
            )}
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <button
              onClick={onNavigateToProtect}
              className="flex items-center gap-2 px-4 py-2 bg-white text-blue-700 rounded-xl text-xs font-bold hover:bg-blue-50 transition-all shadow-md shadow-black/10 active:scale-98"
            >
              <UploadCloud className="w-4 h-4" />
              <span>{t('nav_protect', 'Protect & Embed')}</span>
            </button>

            <button
              onClick={() => onNavigateToVerify()}
              className="flex items-center gap-2 px-4 py-2 bg-blue-800/80 hover:bg-blue-800 text-white border border-blue-400/40 rounded-xl text-xs font-semibold transition-all"
            >
              <Search className="w-4 h-4" />
              <span>{t('nav_verify', 'Inspect & Verify')}</span>
            </button>

            <button
              onClick={onNavigateToCases}
              className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-medium backdrop-blur-sm transition-all"
            >
              <Globe className="w-4 h-4" />
              <span>{t('nav_cases', 'Global Cases')}</span>
            </button>
          </div>
        </div>

        {/* Decorative graphic element */}
        <div className="absolute right-0 top-0 bottom-0 w-1/3 opacity-10 pointer-events-none hidden md:flex items-center justify-center">
          <ShieldCheck className="w-64 h-64 text-white -rotate-12 translate-x-12" />
        </div>
      </div>

      {/* 4 Stat Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs hover:shadow-card transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              {t('dash_stat_assets', 'Protected Assets')}
            </span>
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Database className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900">
              {isAuthenticated ? assets.length : '0'}
            </span>
            <span className="text-xs font-medium text-emerald-600 flex items-center gap-0.5">
              <TrendingUp className="w-3.5 h-3.5" />
              Active
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {t('dash_stat_assets_sub', 'Registered in immutable ledger')}
          </p>
        </div>

        {/* Metric 2 */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs hover:shadow-card transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              {t('dash_stat_verifications', 'Verifications')}
            </span>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900">100%</span>
            <span className="text-xs font-medium text-emerald-600">0.00% FPR</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {t('dash_stat_verif_sub', 'Reported lab benchmark on unattacked images')}
          </p>
        </div>

        {/* Metric 3 */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs hover:shadow-card transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              {t('dash_stat_cases', 'Global Cases')}
            </span>
            <div className="w-9 h-9 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
              <Globe className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900">
              {isAuthenticated ? cases.length : '0'}
            </span>
            <span className="text-xs font-medium text-purple-600">Cross-Border</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {t('dash_stat_cases_sub', 'Active infringement tracking dossiers')}
          </p>
        </div>

        {/* Metric 4 */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs hover:shadow-card transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              {t('dash_stat_coverage', 'Robustness Index')}
            </span>
            <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Lock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900">&gt;42 dB</span>
            <span className="text-xs font-medium text-slate-500">PSNR</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {t('dash_stat_coverage_sub', 'Imperceptible DCT-SVD sub-band modulation')}
          </p>
        </div>
      </div>

      {/* Main Grid: Recent Protected Assets & Recent Global Cases */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Recent Protected Assets */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                {t('dash_recent_assets', 'Recent Protected Assets')}
              </h2>
              <p className="text-xs text-slate-500">
                {t('dash_recent_assets_desc', 'Images secured with DCT-SVD payload and certified Image Identity Passports')}
              </p>
            </div>
            <button
              onClick={onNavigateToVault}
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1 transition-colors"
            >
              <span>{t('dash_open_vault', 'View all vault assets')}</span>
              <ArrowRight className="w-3.5 h-3.5 rtl:rotate-180" />
            </button>
          </div>

          {loading ? (
            <div className="p-12 text-center bg-white rounded-2xl border border-slate-200">
              <div className="inline-block w-7 h-7 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mb-2" />
              <p className="text-xs text-slate-500">Loading catalog...</p>
            </div>
          ) : assets.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-2xl border border-dashed border-slate-300">
              <UploadCloud className="w-10 h-10 text-slate-400 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-800">
                {t('dash_no_recent_assets', 'No protected images yet')}
              </p>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-3">
                Embed your first forensic watermark to safeguard your creative work worldwide.
              </p>
              <button
                onClick={onNavigateToProtect}
                className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition-colors"
              >
                {t('nav_protect', 'Protect Image Now')}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {assets.slice(0, 4).map((asset) => (
                <div
                  key={asset.asset_id}
                  className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs hover:shadow-card hover:border-slate-300 transition-all flex flex-col justify-between group"
                >
                  <div className="space-y-3">
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
                        <span className="text-[10px] text-slate-400 font-mono truncate max-w-[120px]">
                          pHash: {asset.perceptual_hash?.substring(0, 8)}...
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 mt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                    <button
                      onClick={() => onOpenPassport(asset)}
                      className="flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors"
                    >
                      <Award className="w-3.5 h-3.5" />
                      <span>{t('passport_title', 'View Passport')}</span>
                    </button>

                    <button
                      onClick={() => onNavigateToVerify(asset.asset_id)}
                      className="p-1 text-slate-400 hover:text-slate-700 rounded transition-colors"
                      title="Inspect with verify engine"
                    >
                      <Search className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Col: Global Cases & Forensics Activity */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                {t('cases_title', 'Global Cases')}
              </h2>
              <p className="text-xs text-slate-500">{t('dash_cases_subtitle', 'Cross-border misuse tracking')}</p>
            </div>
            <button
              onClick={onNavigateToCases}
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              <span>{t('dash_view_all', 'View all')}</span>
              <ArrowRight className="w-3.5 h-3.5 rtl:rotate-180" />
            </button>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100 shadow-xs">
            {cases.length === 0 ? (
              <div className="p-6 text-center">
                <Globe className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-xs font-semibold text-slate-700">{t('dash_no_cases', 'No active cases')}</p>
                <p className="text-[11px] text-slate-400 mt-0.5 mb-3">
                  {t('dash_no_cases_desc', 'Open an international dossier whenever suspected unauthorized usage is detected.')}
                </p>
                <button
                  onClick={onNavigateToCases}
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-colors"
                >
                  {t('cases_btn_new', 'Open New Case')}
                </button>
              </div>
            ) : (
              cases.slice(0, 4).map((c) => (
                <div
                  key={c.id}
                  onClick={onNavigateToCases}
                  className="p-3.5 hover:bg-slate-50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono font-bold text-blue-700">
                      {c.case_number}
                    </span>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                        c.status === 'Resolved'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : c.status === 'Potential Match'
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {c.status}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-900 mt-1 truncate">
                    {c.title}
                  </p>
                  <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400">
                    {c.suspected_country && (
                      <span className="flex items-center gap-1">
                        <Globe className="w-3 h-3" />
                        {c.suspected_country}
                      </span>
                    )}
                    {c.match_score !== undefined && c.match_score !== null && (
                      <span>&bull; {(c.match_score * 100).toFixed(1)}% Match</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Quick Forensics Lab CTA Banner */}
          <div className="p-4 rounded-xl bg-gradient-to-br from-slate-900 to-slate-800 text-white space-y-2 shadow-sm">
            <div className="flex items-center gap-2 text-blue-400 font-semibold text-xs">
              <FileCheck2 className="w-4 h-4" />
              <span>Forensics &amp; Robustness Lab</span>
            </div>
            <p className="text-xs text-slate-300 leading-snug">
              {t('dash_lab_card_desc', 'Examine empirical robustness benchmarks across JPEG compression (Q=50..90), Gaussian noise, blur, and cropping.')}
            </p>
            <button
              onClick={onNavigateToLab}
              className="mt-2 w-full py-1.5 bg-white/10 hover:bg-white/20 text-white rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-1.5"
            >
              <span>{t('dash_run_forensics', 'Launch Forensics Lab')}</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
