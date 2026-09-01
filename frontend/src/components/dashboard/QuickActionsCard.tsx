import React from 'react';
import { QrCode, ClipboardList, AlertTriangle, Search, ArrowRight } from 'lucide-react';

interface QuickActionsCardProps {
  onScanVerify: () => void;
  onAddInspection: () => void;
  onRegisterComplaint: () => void;
  onSearchLicensee: () => void;
}

export const QuickActionsCard: React.FC<QuickActionsCardProps> = ({
  onScanVerify,
  onAddInspection,
  onRegisterComplaint,
  onSearchLicensee,
}) => {
  const actions = [
    {
      label: 'Scan & Verify Product',
      icon: QrCode,
      gradient: 'from-[#6366f1] via-[#8b5cf6] to-[#a855f7]',
      border: 'border-purple-500/40',
      shadow: 'shadow-purple-900/30',
      onClick: onScanVerify,
    },
    {
      label: 'Add New Inspection',
      icon: ClipboardList,
      gradient: 'from-[#2563eb] via-[#3b82f6] to-[#0284c7]',
      border: 'border-blue-500/40',
      shadow: 'shadow-blue-900/30',
      onClick: onAddInspection,
    },
    {
      label: 'Register Complaint',
      icon: AlertTriangle,
      gradient: 'from-[#db2777] via-[#e11d48] to-[#f43f5e]',
      border: 'border-pink-500/40',
      shadow: 'shadow-pink-900/30',
      onClick: onRegisterComplaint,
    },
    {
      label: 'Search Licensee',
      icon: Search,
      gradient: 'from-[#059669] via-[#10b981] to-[#14b8a6]',
      border: 'border-emerald-500/40',
      shadow: 'shadow-emerald-900/30',
      onClick: onSearchLicensee,
    },
  ];

  return (
    <div className="rounded-2xl bg-[#0d1430] border border-[#1d274d] p-5 shadow-xl flex flex-col justify-between h-full">
      <h3 className="text-sm font-bold text-white tracking-wide mb-3">Quick Actions</h3>

      <div className="space-y-2.5">
        {actions.map((action, idx) => {
          const Icon = action.icon;
          return (
            <button
              key={idx}
              onClick={action.onClick}
              className={`w-full flex items-center justify-between p-3 rounded-xl bg-gradient-to-r ${action.gradient} text-white font-medium text-xs sm:text-sm shadow-lg ${action.shadow} hover:brightness-110 active:scale-[0.99] transition-all duration-150 group border ${action.border}`}
            >
              <div className="flex items-center space-x-3">
                <div className="p-1 rounded-lg bg-white/10 backdrop-blur-sm">
                  <Icon className="w-4 h-4" />
                </div>
                <span className="font-semibold text-xs sm:text-sm">{action.label}</span>
              </div>
              <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
            </button>
          );
        })}
      </div>
    </div>
  );
};
