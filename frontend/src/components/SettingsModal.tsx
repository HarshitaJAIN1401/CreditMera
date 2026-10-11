import React, { useState } from 'react';
import { X, Settings, Globe, Check, Sun } from 'lucide-react';
import { useTranslation } from '../i18n/I18nContext';
import type { SupportedLanguage } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const { t, language, setLanguage, supportedLanguages } = useTranslation();

  const [defaultLicense, setDefaultLicense] = useState(() => {
    return localStorage.getItem('creditmera_default_license') || 'All Rights Reserved';
  });

  const [defaultAlpha, setDefaultAlpha] = useState(() => {
    const saved = localStorage.getItem('creditmera_default_alpha');
    return saved ? parseFloat(saved) : 0.10;
  });

  const [savedMessage, setSavedMessage] = useState(false);

  if (!isOpen) return null;

  const handleSave = () => {
    localStorage.setItem('creditmera_default_license', defaultLicense);
    localStorage.setItem('creditmera_default_alpha', defaultAlpha.toString());
    setSavedMessage(true);
    setTimeout(() => {
      setSavedMessage(false);
      onClose();
    }, 600);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-blue-600" />
            <h3 className="text-base font-bold text-slate-900">
              {t('nav_settings', 'Studio Preferences & Settings')}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4 text-xs">
          {/* Language Selection */}
          <div className="space-y-2">
            <label className="block font-bold text-slate-800 flex items-center gap-1.5">
              <Globe className="w-4 h-4 text-blue-600" />
              <span>Interface Language / बहुभाषी चयन</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {supportedLanguages.map((lang) => {
                const isSelected = language === lang.code;
                return (
                  <button
                    key={lang.code}
                    onClick={() => setLanguage(lang.code as SupportedLanguage)}
                    className={`flex items-center justify-between p-2.5 rounded-xl border text-xs transition-all ${
                      isSelected
                        ? 'border-blue-600 bg-blue-50 text-blue-700 font-bold shadow-xs'
                        : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <span>{lang.flag}</span>
                      <span>{lang.nativeName}</span>
                    </span>
                    {isSelected && <Check className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Theme Enforced Light Mode */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-800 flex items-center gap-1.5">
                <Sun className="w-4 h-4 text-amber-500" />
                <span>Theme Display</span>
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                Light Mode Only
              </span>
            </div>
            <p className="text-[11px] text-slate-500 leading-snug">
              CreditMera is calibrated exclusively in high-contrast professional light aesthetic for accurate color appraisal and forensic image evaluation.
            </p>
          </div>

          {/* Default License */}
          <div>
            <label className="block font-bold text-slate-800 mb-1">
              Default Attribution License
            </label>
            <select
              value={defaultLicense}
              onChange={(e) => setDefaultLicense(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="All Rights Reserved">All Rights Reserved</option>
              <option value="Commercial Production License">Commercial Production License</option>
              <option value="Editorial Use Only">Editorial Use Only</option>
              <option value="Creative Commons CC BY-NC 4.0">Creative Commons CC BY-NC 4.0</option>
              <option value="Creative Commons CC BY 4.0">Creative Commons CC BY 4.0</option>
              <option value="Public Domain / CC0">Public Domain / CC0</option>
            </select>
          </div>

          {/* Default Watermark Alpha */}
          <div>
            <div className="flex justify-between mb-1">
              <label className="font-bold text-slate-800">Default Embedding Alpha</label>
              <span className="font-mono font-bold text-blue-700">&alpha; = {defaultAlpha.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.25"
              step="0.01"
              value={defaultAlpha}
              onChange={(e) => setDefaultAlpha(parseFloat(e.target.value))}
              className="w-full accent-blue-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1">
              <span>0.05 (Subtle)</span>
              <span>0.10 (Recommended)</span>
              <span>0.25 (Maximum Survivability)</span>
            </div>
          </div>

          {savedMessage && (
            <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-center font-bold">
              Preferences saved successfully!
            </div>
          )}

          {/* Actions */}
          <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
            <button
              onClick={onClose}
              className="px-3.5 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-medium transition-colors"
            >
              {t('common_cancel', 'Cancel')}
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold shadow-xs transition-colors"
            >
              {t('common_save', 'Save Preferences')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
