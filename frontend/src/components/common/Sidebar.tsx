import React from 'react';
import {
  LayoutDashboard,
  ScanLine,
  Package,
  Users,
  ClipboardCheck,
  AlertCircle,
  FileBarChart,
  Scale,
  Bell,
  Settings,
  HelpCircle,
  UserRound,
  ShieldCheck,
  ArrowRight
} from 'lucide-react';
import labelLensLogo from '../../assets/labellens-logo.png';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  isOpen: boolean;
  onCloseMobile?: () => void;
  onOpenRightsModal: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  isOpen,
  onCloseMobile,
  onOpenRightsModal,
}) => {
  const mainNavItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'new-inspection', label: 'Scan & Verify', icon: ScanLine },
    { id: 'products', label: 'Products', icon: Package },
    { id: 'licensees', label: 'Licensee Management', icon: Users },
    { id: 'history', label: 'Inspections', icon: ClipboardCheck },
    { id: 'complaints', label: 'Complaints', icon: AlertCircle },
    { id: 'analytics', label: 'Reports & Analytics', icon: FileBarChart },
    { id: 'rules', label: 'Legal Metrology Info', icon: Scale },
  ];

  const secondaryNavItems = [
    { id: 'profile', label: 'Profile', icon: UserRound },
    { id: 'notifications', label: 'Notifications', icon: Bell, badge: '3' },
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'help', label: 'Help & Support', icon: HelpCircle },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 z-40 lg:hidden backdrop-blur-sm"
          onClick={onCloseMobile}
        />
      )}

      <aside
        className={`fixed top-0 left-0 bottom-0 z-50 w-64 bg-[#090e24] border-r border-[#1a2342] flex flex-col justify-between transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Top Section: Logo & Navigation */}
        <div className="flex-1 overflow-y-auto px-4 py-5 scrollbar-thin">
          {/* Logo Header */}
          <div 
            className="flex items-center space-x-3 px-2 mb-8 cursor-pointer group"
            onClick={() => onSelectTab('dashboard')}
          >
            <img
              src={labelLensLogo}
              alt="LabelLens"
              className="h-10 w-10 rounded-xl border border-cyan-300/20 object-contain p-0.5 bg-[#0a1026]/80 shadow-lg shadow-cyan-500/10 transition-transform duration-200 group-hover:scale-105"
            />
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="text-xl font-bold tracking-tight text-white">LabelLens</span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium tracking-wide">
                सही लेबल, सही व्यापार
              </p>
            </div>
          </div>

          {/* Primary Nav List */}
          <div className="space-y-1">
            {mainNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onSelectTab(item.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-600/30'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>

          {/* Divider */}
          <div className="my-4 border-t border-[#1a2342]" />

          {/* Secondary Nav List */}
          <div className="space-y-1">
            {secondaryNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onSelectTab(item.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-600/30'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-purple-600 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Bottom Card: Know Your Rights */}
        <div className="p-4">
          <div className="relative rounded-2xl bg-gradient-to-b from-[#131b3e] to-[#0c1328] border border-[#232f58] p-4 text-center shadow-xl overflow-hidden group">
            {/* Background ambient glow */}
            <div className="absolute -top-10 -right-10 w-24 h-24 bg-purple-500/10 rounded-full blur-xl pointer-events-none" />
            
            <div className="flex justify-center mb-2.5">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <ShieldCheck className="w-5 h-5" />
              </div>
            </div>

            <h4 className="text-xs font-bold text-blue-300">
              Ensure Accuracy. Ensure Trust.
            </h4>
            <p className="text-[10px] text-slate-400 mt-1 mb-3">
              Legal Metrology for a Fairer India.
            </p>

            <button
              onClick={onOpenRightsModal}
              className="w-full flex items-center justify-center space-x-1.5 py-2 px-3 rounded-xl bg-gradient-to-r from-purple-700/60 to-indigo-700/60 hover:from-purple-600 hover:to-indigo-600 border border-purple-500/30 text-white text-xs font-semibold shadow-md transition-all duration-200"
            >
              <span>Know Your Rights</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};
