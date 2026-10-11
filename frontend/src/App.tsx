import React, { useState } from 'react';
import { AuthProvider } from './context/AuthContext';
import { I18nProvider, useTranslation } from './i18n/I18nContext';
import { Sidebar } from './components/Sidebar';
import type { NavTab } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { DashboardTab } from './components/DashboardTab';
import { ProtectTab } from './components/ProtectTab';
import { VerifyTab } from './components/VerifyTab';
import { AssetVaultTab } from './components/AssetVaultTab';
import { PassportTab } from './components/PassportTab';
import { RobustnessLabTab } from './components/RobustnessLabTab';
import { GlobalCasesTab } from './components/GlobalCasesTab';
import { ReceiptVerifyTab } from './components/ReceiptVerifyTab';
import { AuthModal } from './components/AuthModal';
import { ProfileModal } from './components/ProfileModal';
import { SettingsModal } from './components/SettingsModal';
import { HelpModal } from './components/HelpModal';
import { PassportModal } from './components/PassportModal';
import { Footer } from './components/Footer';
import type { AssetSummary } from './types';

export const MainContent: React.FC = () => {
  const { isRTL } = useTranslation();

  // Navigation & Layout State
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Modals State
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [helpModalOpen, setHelpModalOpen] = useState(false);

  // Cross-Tab Navigation Parameters
  const [verifyInitialAssetId, setVerifyInitialAssetId] = useState<number | undefined>(undefined);
  const [vaultSearchQuery, setVaultSearchQuery] = useState<string>('');
  const [caseInitialParams, setCaseInitialParams] = useState<{
    assetId?: number;
    suspectedUrl?: string;
    matchScore?: number;
    watermarkStatus?: string;
  }>({});

  // Passport modal standalone
  const [modalPassportAsset, setModalPassportAsset] = useState<AssetSummary | null>(null);
  const [modalPassportAssetId, setModalPassportAssetId] = useState<number | null>(null);

  // Navigation handlers
  const handleNavigateToProtect = () => {
    setActiveTab('protect');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNavigateToVerify = (assetId?: number) => {
    setVerifyInitialAssetId(assetId);
    setActiveTab('verify');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNavigateToVault = (searchQuery: string = '') => {
    setVaultSearchQuery(searchQuery);
    setActiveTab('vault');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNavigateToCases = (
    assetId?: number,
    suspectedUrl?: string,
    matchScore?: number,
    watermarkStatus?: string
  ) => {
    setCaseInitialParams({ assetId, suspectedUrl, matchScore, watermarkStatus });
    setActiveTab('cases');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNavigateToLab = () => {
    setActiveTab('lab');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenPassportModal = (assetOrId: AssetSummary | number) => {
    if (typeof assetOrId === 'number') {
      setModalPassportAssetId(assetOrId);
      setModalPassportAsset(null);
    } else {
      setModalPassportAsset(assetOrId);
      setModalPassportAssetId(assetOrId.asset_id);
    }
  };

  const handleGlobalSearch = (query: string) => {
    handleNavigateToVault(query);
  };

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-900 selection:bg-blue-600 selection:text-white">
      {/* Persistent Left Sidebar (Desktop) */}
      <div className="hidden lg:block">
        <Sidebar
          activeTab={activeTab}
          setActiveTab={(tab) => {
            setActiveTab(tab);
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
          collapsed={sidebarCollapsed}
          setCollapsed={setSidebarCollapsed}
          onOpenProfile={() => setProfileModalOpen(true)}
          onOpenSettings={() => setSettingsModalOpen(true)}
          onOpenHelp={() => setHelpModalOpen(true)}
        />
      </div>

      {/* Mobile Sidebar Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="relative z-10 w-72 bg-white h-full shadow-2xl flex flex-col">
            <Sidebar
              activeTab={activeTab}
              setActiveTab={(tab) => {
                setActiveTab(tab);
                setMobileMenuOpen(false);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              collapsed={false}
              setCollapsed={() => {}}
              onOpenProfile={() => {
                setMobileMenuOpen(false);
                setProfileModalOpen(true);
              }}
              onOpenSettings={() => {
                setMobileMenuOpen(false);
                setSettingsModalOpen(true);
              }}
              onOpenHelp={() => {
                setMobileMenuOpen(false);
                setHelpModalOpen(true);
              }}
            />
          </div>
        </div>
      )}

      {/* Main Content Container with dynamic margins for desktop sidebar */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${
          isRTL
            ? sidebarCollapsed
              ? 'lg:mr-20'
              : 'lg:mr-64'
            : sidebarCollapsed
            ? 'lg:ml-20'
            : 'lg:ml-64'
        }`}
      >
        {/* Top Sticky Navbar */}
        <Navbar
          activeTab={activeTab}
          setActiveTab={(tab) => {
            setActiveTab(tab);
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
          onOpenAuth={() => setAuthModalOpen(true)}
          onOpenProfile={() => setProfileModalOpen(true)}
          onOpenSettings={() => setSettingsModalOpen(true)}
          onToggleMobileMenu={() => setMobileMenuOpen(true)}
          onGlobalSearch={handleGlobalSearch}
        />

        {/* Workspace Tab View */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
          {activeTab === 'dashboard' && (
            <DashboardTab
              onNavigateToProtect={handleNavigateToProtect}
              onNavigateToVerify={handleNavigateToVerify}
              onNavigateToVault={handleNavigateToVault}
              onNavigateToCases={handleNavigateToCases}
              onNavigateToLab={handleNavigateToLab}
              onOpenPassport={handleOpenPassportModal}
            />
          )}

          {activeTab === 'protect' && (
            <ProtectTab
              onOpenAuth={() => setAuthModalOpen(true)}
              onNavigateToVerify={handleNavigateToVerify}
            />
          )}

          {activeTab === 'verify' && (
            <VerifyTab
              initialAssetId={verifyInitialAssetId}
              onNavigateToCases={handleNavigateToCases}
              onOpenPassport={(id) => handleOpenPassportModal(id)}
            />
          )}

          {activeTab === 'vault' && (
            <AssetVaultTab
              onOpenAuth={() => setAuthModalOpen(true)}
              onNavigateToProtect={handleNavigateToProtect}
              onNavigateToVerify={handleNavigateToVerify}
              onNavigateToCases={(id) => handleNavigateToCases(id)}
              onOpenPassport={handleOpenPassportModal}
              initialSearchQuery={vaultSearchQuery}
            />
          )}

          {activeTab === 'passport' && (
            <PassportTab
              onNavigateToProtect={handleNavigateToProtect}
              onNavigateToVerify={handleNavigateToVerify}
              initialAssetId={modalPassportAssetId || undefined}
            />
          )}

          {activeTab === 'lab' && <RobustnessLabTab />}

          {activeTab === 'cases' && (
            <GlobalCasesTab
              onNavigateToVerify={handleNavigateToVerify}
              initialCreateAssetId={caseInitialParams.assetId}
              initialSuspectedUrl={caseInitialParams.suspectedUrl}
              initialMatchScore={caseInitialParams.matchScore}
              initialWatermarkStatus={caseInitialParams.watermarkStatus}
            />
          )}

          {activeTab === 'receipts' && <ReceiptVerifyTab />}
        </main>

        {/* Footer */}
        <Footer />
      </div>

      {/* Global Modals */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
      />

      <ProfileModal
        isOpen={profileModalOpen}
        onClose={() => setProfileModalOpen(false)}
        onOpenAuth={() => setAuthModalOpen(true)}
      />

      <SettingsModal
        isOpen={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
      />

      <HelpModal
        isOpen={helpModalOpen}
        onClose={() => setHelpModalOpen(false)}
      />

      {modalPassportAssetId !== null && (
        <PassportModal
          isOpen={modalPassportAssetId !== null}
          onClose={() => {
            setModalPassportAssetId(null);
            setModalPassportAsset(null);
          }}
          assetId={modalPassportAssetId}
          initialAsset={modalPassportAsset}
        />
      )}
    </div>
  );
};

export default function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <MainContent />
      </AuthProvider>
    </I18nProvider>
  );
}
