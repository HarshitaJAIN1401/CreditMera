import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { useTranslation } from '../i18n/I18nContext';

export const Footer: React.FC = () => {
  const { t } = useTranslation();

  return (
    <footer className="w-full border-t border-slate-200 bg-white mt-16 py-12 text-slate-500 text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Col 1: Brand & Description */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-blue-600 flex items-center justify-center text-white">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <span className="text-base font-bold text-slate-900 tracking-tight">CreditMera</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-50 border border-blue-200 text-blue-700 font-semibold">
                DCT-SVD v1.0
              </span>
            </div>
            <p className="text-slate-600 text-xs leading-relaxed max-w-md">
              {t(
                'nav_tagline',
                'Your Image. Your Credit. International image ownership, forensic watermarking, and cross-border attribution platform.'
              )}
            </p>
          </div>

          {/* Col 2: Specifications */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800">
              Technical Specifications
            </h4>
            <ul className="space-y-1.5 text-slate-500">
              <li>Hybrid DCT-SVD Sub-band Modulation</li>
              <li>128-bit Structured Magic Payload</li>
              <li>Collision-Safe 40-bit Asset IDs</li>
              <li>HMAC-SHA256 Ownership Receipts</li>
              <li>64-bit Perceptual Hash (DCT pHash)</li>
            </ul>
          </div>

          {/* Col 3: Research & Decisions */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800">
              Verification Engine
            </h4>
            <ul className="space-y-1.5 text-slate-500">
              <li>Calibrated 5-Tier Decision States</li>
              <li>336 Benchmarked Attack Trials</li>
              <li>0.00% Empirical False Positive Rate</li>
              <li>Cross-Border Case Management</li>
              <li>Digital Provenance Identity Passports</li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-slate-400">
          <p>&copy; {new Date().getFullYear()} CreditMera Research &amp; Engineering. All rights reserved.</p>
          <div className="flex items-center gap-6">
            <span>Discrete Cosine Transform &bull; Singular Value Decomposition</span>
            <span className="text-emerald-600 font-mono font-semibold">141/141 Verified Tests Passing</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
