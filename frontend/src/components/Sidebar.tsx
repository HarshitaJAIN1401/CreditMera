import React from 'react';
import {
  LayoutDashboard,
  UploadCloud,
  Search,
  Database,
  Award,
  FlaskConical,
  Globe,
  FileCheck2,
  User as UserIcon,
  Settings as SettingsIcon,
  HelpCircle,
  Shield,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useTranslation } from '../i18n/I18nContext';
import { useAuth } from '../context/AuthContext';

export type NavTab =
  | 'dashboard'
  | 'protect'
  | 'verify'
  | 'vault'
  | 'passport'
  | 'lab'
  | 'cases'
  | 'receipts';

interface SidebarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
  onOpenProfile: () => void;
  onOpenSettings: () => void;
  onOpenHelp: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  collapsed,
  setCollapsed,
  onOpenProfile,
  onOpenSettings,
  onOpenHelp,
}) => {
  const { t, isRTL } = useTranslation();
  const { isAuthenticated, user } = useAuth();

  const mainNavItems: { id: NavTab; label: string; icon: React.ReactNode; badge?: string }[] = [
    {
      id: 'dashboard',
      label: t('nav_dashboard', 'Dashboard'),
      icon: <LayoutDashboard className="w-5 h-5 flex-shrink-0" />,
    },
    {
      id: 'protect',
      label: t('nav_protect', 'Protect & Embed'),
      icon: <UploadCloud className="w-5 h-5 flex-shrink-0" />,
    },
    {
      id: 'verify',
      label: t('nav_verify', 'Verify & Inspect'),
      icon: <Search className="w-5 h-5 flex-shrink-0" />,
    },
    {
      id: 'vault',
      label: t('nav_vault', 'Asset Vault'),
      icon: <Database className="w-5 h-5 flex-shrink-0" />,
    },
    {
      id: 'passport',
      label: t('nav_passport', 'Identity Passport'),
      icon: <Award className="w-5 h-5 flex-shrink-0" />,
      badge: 'New',
    },
    {
      id: 'lab',
      label: t('nav_forensics', 'Forensics Lab'),
      icon: <FlaskConical className="w-5 h-5 flex-shrink-0" />,
    },
    {
      id: 'cases',
      label: t('nav_cases', 'Global Cases'),
      icon: <Globe className="w-5 h-5 flex-shrink-0" />,
      badge: 'Cross-Border',
    },
    {
      id: 'receipts',
      label: t('nav_receipts', 'Receipt Verifier'),
      icon: <FileCheck2 className="w-5 h-5 flex-shrink-0" />,
    },
  ];

  return (
    <aside
      className={`fixed inset-y-0 ${
        isRTL ? 'right-0' : 'left-0'
      } z-30 flex flex-col bg-white border-r rtl:border-r-0 rtl:border-l border-slate-200 transition-all duration-300 shadow-sm ${
        collapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-slate-100">
        <div
          onClick={() => setActiveTab('dashboard')}
          className="flex items-center gap-3 cursor-pointer overflow-hidden select-none"
        >
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 flex-shrink-0">
            <Shield className="w-5 h-5" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <span className="block text-base font-bold text-slate-900 tracking-tight leading-none">
                CreditMera
              </span>
              <span className="block text-[11px] text-blue-600 font-medium tracking-normal mt-1 truncate">
                {t('nav_tagline', 'Your Image. Your Credit.')}
              </span>
            </div>
          )}
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors hidden lg:flex items-center justify-center"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            isRTL ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
          ) : (
            isRTL ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Main Navigation List */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <div className="px-3 pb-2">
          {!collapsed && (
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
              Workspaces
            </span>
          )}
        </div>
        {mainNavItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              title={collapsed ? item.label : undefined}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? 'bg-blue-50 text-blue-700 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              } ${collapsed ? 'justify-center' : ''}`}
            >
              <span className={isActive ? 'text-blue-600' : 'text-slate-500'}>{item.icon}</span>
              {!collapsed && (
                <div className="flex-1 flex items-center justify-between text-start truncate">
                  <span className="truncate">{item.label}</span>
                  {item.badge && (
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                        isActive
                          ? 'bg-blue-200/60 text-blue-800'
                          : 'bg-slate-100 text-slate-600 border border-slate-200'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}

        {/* Separator */}
        <div className="pt-4 pb-2 px-3">
          <div className="border-t border-slate-200/70" />
          {!collapsed && (
            <span className="block pt-3 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
              Management &amp; Tools
            </span>
          )}
        </div>

        {/* Lower Navigation Items */}
        <button
          onClick={onOpenProfile}
          title={collapsed ? t('nav_profile', 'Profile') : undefined}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors ${
            collapsed ? 'justify-center' : ''
          }`}
        >
          <UserIcon className="w-5 h-5 text-slate-500 flex-shrink-0" />
          {!collapsed && (
            <span className="flex-1 text-start truncate">
              {isAuthenticated && user?.full_name ? user.full_name : t('nav_profile', 'Creator Profile')}
            </span>
          )}
        </button>

        <button
          onClick={onOpenSettings}
          title={collapsed ? t('nav_settings', 'Settings') : undefined}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors ${
            collapsed ? 'justify-center' : ''
          }`}
        >
          <SettingsIcon className="w-5 h-5 text-slate-500 flex-shrink-0" />
          {!collapsed && <span className="flex-1 text-start truncate">{t('nav_settings', 'Settings')}</span>}
        </button>

        <button
          onClick={onOpenHelp}
          title={collapsed ? t('nav_help', 'Help & Documentation') : undefined}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors ${
            collapsed ? 'justify-center' : ''
          }`}
        >
          <HelpCircle className="w-5 h-5 text-slate-500 flex-shrink-0" />
          {!collapsed && <span className="flex-1 text-start truncate">{t('nav_help', 'Help & Guides')}</span>}
        </button>
      </div>

      {/* System Status Footer */}
      <div className="p-3 border-t border-slate-100 bg-slate-50/50">
        {!collapsed ? (
          <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white border border-slate-200/80 shadow-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <span className="block text-[11px] font-semibold text-slate-800 leading-tight">
                Engine Active
              </span>
              <span className="block text-[10px] text-slate-500 truncate">
                DCT-SVD &bull; 5-Tier Verification
              </span>
            </div>
          </div>
        ) : (
          <div className="flex justify-center" title="System Active">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          </div>
        )}
      </div>
    </aside>
  );
};
