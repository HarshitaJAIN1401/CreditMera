import React, { useState, useRef, useEffect } from 'react';
import {
  Search,
  Globe,
  Bell,
  User as UserIcon,
  LogOut,
  LogIn,
  Menu,
  Check,
  ShieldCheck,
  FileCheck,
  ExternalLink,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../i18n/I18nContext';
import type { NavTab } from './Sidebar';
import type { SupportedLanguage } from '../types';

interface NavbarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  onOpenAuth: () => void;
  onOpenProfile: () => void;
  onOpenSettings: () => void;
  onToggleMobileMenu?: () => void;
  onGlobalSearch?: (query: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab: _activeTab,
  setActiveTab,
  onOpenAuth,
  onOpenProfile,
  onOpenSettings,
  onToggleMobileMenu,
  onGlobalSearch,
}) => {
  const { user, isAuthenticated, logout } = useAuth();
  const { t, language, setLanguage, supportedLanguages, isRTL } = useTranslation();

  const [langDropdownOpen, setLangDropdownOpen] = useState(false);
  const [notifDropdownOpen, setNotifDropdownOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const langRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (langRef.current && !langRef.current.contains(e.target as Node)) {
        setLangDropdownOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifDropdownOpen(false);
      }
      if (userRef.current && !userRef.current.contains(e.target as Node)) {
        setUserDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      if (onGlobalSearch) {
        onGlobalSearch(searchQuery.trim());
      } else {
        setActiveTab('vault');
      }
    }
  };

  const currentLang = supportedLanguages.find((l) => l.code === language) || supportedLanguages[0];

  const recentNotifications = [
    {
      id: '1',
      title: 'DCT-SVD Engine Verified',
      desc: 'Empirical benchmark with 0.00% FPR across 336 trials.',
      time: 'Just now',
      icon: <ShieldCheck className="w-4 h-4 text-emerald-500" />,
    },
    {
      id: '2',
      title: 'HMAC Cryptographic Key Active',
      desc: 'Platform registration receipts signed with HMAC-SHA256.',
      time: '1h ago',
      icon: <FileCheck className="w-4 h-4 text-blue-500" />,
    },
    {
      id: '3',
      title: 'Perceptual Hash Indexing Ready',
      desc: 'Fast 64-bit DCT pHash and SSIM visual similarity enabled.',
      time: 'Today',
      icon: <Globe className="w-4 h-4 text-purple-500" />,
    },
  ];

  return (
    <header className="sticky top-0 z-20 w-full bg-white/95 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Mobile hamburger button */}
          <div className="flex items-center gap-2 lg:hidden">
            <button
              onClick={onToggleMobileMenu}
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg"
              aria-label="Toggle menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div
              onClick={() => setActiveTab('dashboard')}
              className="flex items-center gap-2 cursor-pointer font-bold text-slate-900"
            >
              <span className="text-blue-600 text-lg font-black">CreditMera</span>
            </div>
          </div>

          {/* Global Search Input */}
          <div className="flex-1 max-w-md hidden sm:block">
            <form onSubmit={handleSearchSubmit} className="relative">
              <Search
                className={`absolute top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 ${
                  isRTL ? 'right-3' : 'left-3'
                }`}
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('nav_search_placeholder', 'Search assets, IDs, countries or perceptual hash...')}
                className={`w-full py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white text-slate-900 placeholder-slate-400 transition-all ${
                  isRTL ? 'pr-9 pl-3' : 'pl-9 pr-3'
                }`}
              />
            </form>
          </div>

          {/* Right Controls: Language Selector, Notifications, User Profile */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Language Selector Dropdown */}
            <div className="relative" ref={langRef}>
              <button
                onClick={() => setLangDropdownOpen(!langDropdownOpen)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors"
                title="Select language"
              >
                <span className="text-sm leading-none">{currentLang.flag}</span>
                <span className="hidden md:inline">{currentLang.nativeName}</span>
              </button>

              {langDropdownOpen && (
                <div
                  className={`absolute top-full mt-1.5 w-48 bg-white border border-slate-200 rounded-xl shadow-lg py-1 z-50 animate-in fade-in slide-in-from-top-1 duration-150 ${
                    isRTL ? 'left-0' : 'right-0'
                  }`}
                >
                  <div className="px-3 py-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                    Select Language / भाषा
                  </div>
                  {supportedLanguages.map((lang) => {
                    const isSelected = language === lang.code;
                    return (
                      <button
                        key={lang.code}
                        onClick={() => {
                          setLanguage(lang.code as SupportedLanguage);
                          setLangDropdownOpen(false);
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2 text-xs transition-colors ${
                          isSelected
                            ? 'bg-blue-50 text-blue-700 font-semibold'
                            : 'text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span>{lang.flag}</span>
                          <span>{lang.nativeName}</span>
                          <span className="text-slate-400 text-[11px]">({lang.name})</span>
                        </div>
                        {isSelected && <Check className="w-3.5 h-3.5 text-blue-600" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Notifications Popover */}
            <div className="relative" ref={notifRef}>
              <button
                onClick={() => setNotifDropdownOpen(!notifDropdownOpen)}
                className="relative p-2 rounded-lg border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
                title="Notifications"
              >
                <Bell className="w-4 h-4" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-blue-600 ring-2 ring-white" />
              </button>

              {notifDropdownOpen && (
                <div
                  className={`absolute top-full mt-1.5 w-80 bg-white border border-slate-200 rounded-xl shadow-xl py-2 z-50 animate-in fade-in duration-150 ${
                    isRTL ? 'left-0' : 'right-0'
                  }`}
                >
                  <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-100">
                    <span className="text-xs font-semibold text-slate-900">Security &amp; Audit Events</span>
                    <span className="text-[10px] text-blue-600 font-medium cursor-pointer">Mark read</span>
                  </div>
                  <div className="divide-y divide-slate-100 max-h-72 overflow-y-auto">
                    {recentNotifications.map((notif) => (
                      <div key={notif.id} className="p-3 hover:bg-slate-50 transition-colors">
                        <div className="flex items-start gap-2.5">
                          <div className="mt-0.5">{notif.icon}</div>
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-semibold text-slate-800 leading-tight">
                              {notif.title}
                            </p>
                            <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">
                              {notif.desc}
                            </p>
                            <span className="text-[10px] text-slate-400 mt-1 block">{notif.time}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* User Profile / Auth Button */}
            {isAuthenticated ? (
              <div className="relative" ref={userRef}>
                <button
                  onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                  className="flex items-center gap-2 pl-2 pr-2.5 py-1 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
                >
                  <div className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">
                    {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
                  </div>
                  <div className="hidden sm:block text-start">
                    <span className="block text-xs font-semibold text-slate-800 leading-none truncate max-w-[100px]">
                      {user?.full_name || 'Creator'}
                    </span>
                    <span className="block text-[10px] text-slate-400 truncate max-w-[100px]">
                      {user?.email}
                    </span>
                  </div>
                </button>

                {userDropdownOpen && (
                  <div
                    className={`absolute top-full mt-1.5 w-52 bg-white border border-slate-200 rounded-xl shadow-xl py-1 z-50 animate-in fade-in duration-150 ${
                      isRTL ? 'left-0' : 'right-0'
                    }`}
                  >
                    <div className="px-3 py-2 border-b border-slate-100">
                      <p className="text-xs font-semibold text-slate-900 truncate">
                        {user?.full_name || 'Creator'}
                      </p>
                      <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
                    </div>
                    <button
                      onClick={() => {
                        setUserDropdownOpen(false);
                        onOpenProfile();
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 text-start"
                    >
                      <UserIcon className="w-3.5 h-3.5 text-slate-400" />
                      <span>{t('nav_profile', 'Profile')}</span>
                    </button>
                    <button
                      onClick={() => {
                        setUserDropdownOpen(false);
                        onOpenSettings();
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50 text-start"
                    >
                      <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                      <span>{t('nav_settings', 'Settings')}</span>
                    </button>
                    <div className="border-t border-slate-100 my-1" />
                    <button
                      onClick={() => {
                        setUserDropdownOpen(false);
                        logout();
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs text-rose-600 hover:bg-rose-50 text-start font-medium"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>{t('nav_logout', 'Sign Out')}</span>
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={onOpenAuth}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all shadow-blue-500/10"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>{t('nav_login', 'Sign In')}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
