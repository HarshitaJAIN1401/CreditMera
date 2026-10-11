import React from 'react';
import { X, User, Mail, ShieldCheck, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../i18n/I18nContext';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenAuth: () => void;
}

export const ProfileModal: React.FC<ProfileModalProps> = ({
  isOpen,
  onClose,
  onOpenAuth,
}) => {
  const { user, isAuthenticated, logout } = useAuth();
  const { t } = useTranslation();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <User className="w-5 h-5 text-blue-600" />
            <h3 className="text-base font-bold text-slate-900">
              {t('nav_profile', 'Creator Profile')}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {!isAuthenticated ? (
          <div className="text-center py-6 space-y-4">
            <User className="w-12 h-12 text-slate-300 mx-auto" />
            <div>
              <p className="text-sm font-bold text-slate-900">Not signed in</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Sign in to manage your digital ownership registry and account settings.
              </p>
            </div>
            <button
              onClick={() => {
                onClose();
                onOpenAuth();
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs"
            >
              Sign In Now
            </button>
          </div>
        ) : (
          <div className="space-y-5 text-xs">
            {/* User Header */}
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center text-lg font-black shadow-md shadow-blue-500/10">
                {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="min-w-0 flex-1">
                <h4 className="text-sm font-bold text-slate-900 truncate">
                  {user?.full_name || 'Verified Creator'}
                </h4>
                <p className="text-slate-500 truncate flex items-center gap-1 mt-0.5">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  {user?.email}
                </p>
              </div>
            </div>

            {/* Account Details */}
            <div className="space-y-2.5">
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500 font-medium">Account Status:</span>
                <span className="font-semibold text-emerald-600 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Verified Active Creator
                </span>
              </div>

              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500 font-medium">Account ID:</span>
                <span className="font-mono text-slate-700">{user?.id?.substring(0, 16)}...</span>
              </div>

              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500 font-medium">Watermark Key Access:</span>
                <span className="font-mono text-blue-700 font-semibold">128-bit Magic Header (0xC1)</span>
              </div>

              <div className="flex justify-between py-1.5">
                <span className="text-slate-500 font-medium">Attribution Protocol:</span>
                <span className="text-slate-800 font-semibold">DCT-SVD v1.0 Standard</span>
              </div>
            </div>

            {/* Sign Out Button */}
            <div className="pt-2 border-t border-slate-100">
              <button
                onClick={() => {
                  logout();
                  onClose();
                }}
                className="w-full py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-lg font-semibold flex items-center justify-center gap-1.5 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span>Sign Out of Account</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
