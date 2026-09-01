import React, { useState } from 'react';
import { Sidebar } from './components/common/Sidebar';
import { TopHeader } from './components/common/TopHeader';
import { DashboardPage } from './pages/DashboardPage';
import { NewInspectionPage } from './pages/NewInspectionPage';
import { InspectionDetailPage } from './pages/InspectionDetailPage';
import { HistoryPage } from './pages/HistoryPage';
import { RulesPage } from './pages/RulesPage';
import { SystemStatusPage } from './pages/SystemStatusPage';
import { InspectionResponse } from './types/inspection';

import { RegisterComplaintModal } from './components/modals/RegisterComplaintModal';
import { SearchLicenseeModal } from './components/modals/SearchLicenseeModal';
import { KnowYourRightsModal } from './components/modals/KnowYourRightsModal';
import { LegalChatbotModal } from './components/modals/LegalChatbotModal';
import { NotificationsModal } from './components/modals/NotificationsModal';
import { AuthPage } from './pages/AuthPage';
import { ProfilePage } from './pages/ProfilePage';
import { useAuth } from './auth/AuthContext';

export function App() {
  const { user, loading, logout } = useAuth();
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [selectedInspectionId, setSelectedInspectionId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Modals state
  const [isComplaintOpen, setIsComplaintOpen] = useState(false);
  const [isLicenseeOpen, setIsLicenseeOpen] = useState(false);
  const [isRightsOpen, setIsRightsOpen] = useState(false);
  const [isChatbotOpen, setIsChatbotOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);

  const handleOpenInspectionDetail = (id: string) => {
    setSelectedInspectionId(id);
    setCurrentTab('inspection-detail');
  };

  const handleInspectionCompleted = (result: InspectionResponse) => {
    setSelectedInspectionId(result.id);
    setCurrentTab('inspection-detail');
  };

  const handleSelectTab = (tab: string) => {
    if (tab === 'notifications') {
      setIsNotificationsOpen(true);
      return;
    }
    if (tab === 'complaints') {
      setIsComplaintOpen(true);
      return;
    }
    if (tab === 'licensees') {
      setIsLicenseeOpen(true);
      return;
    }

    setCurrentTab(tab);
    if (tab !== 'inspection-detail') {
      setSelectedInspectionId(null);
    }
  };

  if (loading) return <div className="min-h-screen bg-[#080c1d] flex items-center justify-center text-sm text-slate-400">Restoring your secure session…</div>;
  if (!user) return <AuthPage />;
  return (
    <div className="min-h-screen bg-[#080c1d] text-slate-100 flex flex-col font-sans antialiased">
      {/* Left Fixed Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={handleSelectTab}
        isOpen={isSidebarOpen}
        onCloseMobile={() => setIsSidebarOpen(false)}
        onOpenRightsModal={() => setIsRightsOpen(true)}
      />

      {/* Main Wrapper (Offset for fixed sidebar on lg screens) */}
      <div className="lg:pl-64 flex flex-col flex-1 min-h-screen">
        {/* Top Header */}
        <TopHeader
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onOpenNotifications={() => setIsNotificationsOpen(true)}
          user={user}
          onLogout={() => { logout().catch(() => undefined); }}
        />

        {/* Content Area */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1600px] w-full mx-auto">
          {currentTab === 'dashboard' && (
            <DashboardPage
              onNewInspection={() => setCurrentTab('new-inspection')}
              onViewInspection={handleOpenInspectionDetail}
              onViewHistory={() => setCurrentTab('history')}
              onOpenComplaintModal={() => setIsComplaintOpen(true)}
              onOpenLicenseeModal={() => setIsLicenseeOpen(true)}
              onOpenChatbot={() => setIsChatbotOpen(true)}
            />
          )}

          {currentTab === 'new-inspection' && (
            <div className="space-y-4">
              <button
                onClick={() => setCurrentTab('dashboard')}
                className="text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1 mb-2"
              >
                &larr; Back to Dashboard
              </button>
              <NewInspectionPage
                onInspectionComplete={handleInspectionCompleted}
              />
            </div>
          )}

          {currentTab === 'inspection-detail' && selectedInspectionId && (
            <InspectionDetailPage
              inspectionId={selectedInspectionId}
              onBack={() => setCurrentTab('history')}
            />
          )}

          {currentTab === 'history' && (
            <div className="space-y-4">
              <button
                onClick={() => setCurrentTab('dashboard')}
                className="text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1 mb-2"
              >
                &larr; Back to Dashboard
              </button>
              <HistoryPage
                onSelectInspection={handleOpenInspectionDetail}
              />
            </div>
          )}

          {currentTab === 'rules' && (
            <div className="space-y-4">
              <button
                onClick={() => setCurrentTab('dashboard')}
                className="text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1 mb-2"
              >
                &larr; Back to Dashboard
              </button>
              <RulesPage />
            </div>
          )}

          {currentTab === 'status' && (
            <div className="space-y-4">
              <button
                onClick={() => setCurrentTab('dashboard')}
                className="text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1 mb-2"
              >
                &larr; Back to Dashboard
              </button>
              <SystemStatusPage />
            </div>
          )}

          {currentTab === 'products' && (
            <div className="space-y-4">
              <button
                onClick={() => setCurrentTab('dashboard')}
                className="text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1 mb-2"
              >
                &larr; Back to Dashboard
              </button>
              <HistoryPage onSelectInspection={handleOpenInspectionDetail} />
            </div>
          )}

          {currentTab === 'analytics' && (
            <div className="space-y-4">
              <button
                onClick={() => setCurrentTab('dashboard')}
                className="text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1 mb-2"
              >
                &larr; Back to Dashboard
              </button>
              <RulesPage />
            </div>
          )}

          {currentTab === 'profile' && <ProfilePage />}
        </main>
      </div>

      {/* Interactive Modals */}
      <RegisterComplaintModal
        isOpen={isComplaintOpen}
        onClose={() => setIsComplaintOpen(false)}
      />

      <SearchLicenseeModal
        isOpen={isLicenseeOpen}
        onClose={() => setIsLicenseeOpen(false)}
      />

      <KnowYourRightsModal
        isOpen={isRightsOpen}
        onClose={() => setIsRightsOpen(false)}
      />

      <LegalChatbotModal
        isOpen={isChatbotOpen}
        onClose={() => setIsChatbotOpen(false)}
      />

      <NotificationsModal
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
      />
    </div>
  );
}

export default App;
