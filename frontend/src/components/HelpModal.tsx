import React from 'react';
import { X, HelpCircle, ShieldCheck, Layers, Globe, Fingerprint } from 'lucide-react';
import { useTranslation } from '../i18n/I18nContext';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 sm:p-8 space-y-6 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-blue-600" />
            <h3 className="text-base font-bold text-slate-900">
              {t('nav_help', 'CreditMera Documentation & Architecture Guide')}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto space-y-5 text-xs pr-1">
          {/* Section 1: DCT-SVD */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
            <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
              <ShieldCheck className="w-4 h-4 text-blue-600" />
              <span>1. Hybrid DCT-SVD Frequency Watermarking</span>
            </div>
            <p className="text-slate-600 leading-relaxed">
              CreditMera divides luminance channels into 8&times;8 pixel blocks, transforms them into the 2D frequency domain using the Discrete Cosine Transform (DCT), and applies Singular Value Decomposition (SVD) to mid-frequency sub-bands. The 128-bit payload is imperceptibly embedded into the largest singular values with modulation strength &alpha;.
            </p>
          </div>

          {/* Section 2: 5-Tier Decisions */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
            <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
              <Fingerprint className="w-4 h-4 text-emerald-600" />
              <span>2. The 5-Tier Verification Decisions</span>
            </div>
            <ul className="space-y-1.5 text-slate-600 list-disc list-inside">
              <li><strong className="text-emerald-700">MATCHED:</strong> Cryptographic watermark extracted and matches authoritative database ledger.</li>
              <li><strong className="text-slate-700">NOT_DETECTED:</strong> No recognizable signal found in frequency coefficients.</li>
              <li><strong className="text-rose-700">INVALID_WATERMARK:</strong> Candidate header detected but CRC or HMAC fails (corrupted/tampered).</li>
              <li><strong className="text-blue-700">NO_REGISTERED_RECORD:</strong> Valid watermark extracted, but no record exists in database.</li>
              <li><strong className="text-amber-700">INCONCLUSIVE:</strong> Extraction confidence is borderline due to heavy compression or resizing.</li>
            </ul>
          </div>

          {/* Section 3: Visual Similarity vs Frequency Watermarking */}
          <div className="p-4 bg-purple-50/60 rounded-xl border border-purple-200 space-y-2">
            <div className="flex items-center gap-2 font-bold text-purple-900 text-sm">
              <Layers className="w-4 h-4 text-purple-600" />
              <span>3. Visual Similarity (DIP) vs Watermark Extraction</span>
            </div>
            <p className="text-purple-950/80 leading-relaxed">
              <strong>Visual Similarity (pHash + SSIM):</strong> Measures structural, color, and perceptual resemblance between two images (useful when an image has been cropped or filtered).
              <br />
              <strong>DCT-SVD Watermark:</strong> Cryptographically proves origin and ownership. Even if two images look completely different, an authentic CreditMera watermark cannot be forged.
            </p>
          </div>

          {/* Section 4: Image Passport & Cases */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
            <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
              <Globe className="w-4 h-4 text-blue-600" />
              <span>4. Image Identity Passports &amp; Global Cases</span>
            </div>
            <p className="text-slate-600 leading-relaxed">
              Every protected image receives a certified digital provenance passport containing its 40-bit ID, SHA-256 hashes, 64-bit pHash, and legal attribution text. When unauthorized copies appear on foreign websites, creators can open a Global Case to compile timestamped technical evidence dossiers for cross-border copyright enforcement.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
          <span className="text-[10px] text-slate-400 font-mono">
            CreditMera Core v2.4 &bull; DCT-SVD Engine Verified
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold transition-colors"
          >
            {t('common_save', 'Close Guide')}
          </button>
        </div>
      </div>
    </div>
  );
};
